import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Query, HTTPException, Request, Depends, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.auth import get_current_user, CurrentUser
from backend.login import service as login_service

load_dotenv()

# ── Candado del Asistente IA ──────────────────────────────────────────────
# Bloqueo opcional con pantalla de "Sitio en construcción". La contraseña se
# valida SIEMPRE en el backend (nunca viaja al JS del navegador). Activable con
# ASSISTANT_LOCK_ENABLED en el .env.
ASSISTANT_LOCK_ENABLED = os.getenv("ASSISTANT_LOCK_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
ASSISTANT_LOCK_PASSWORD = os.getenv("ASSISTANT_LOCK_PASSWORD", "AcertemosLLM")

from backend.db import db_manager
from backend.queries import (
    VENTAS_POR_HORA_QUERY, SITIOS_VENTA_QUERY, PRODUCTOS_QUERY,
    PAGOS_BETPLAY_COMPLETO, RECARGAS_BETPLAY_COMPLETO
)
from backend.excel_parser import parse_metas_excel, parse_promoters_excel
from backend.cache import (
    init_cache_db, get_cached_sales, set_cached_sales, clear_cache,
    seed_promoters_from_excel, get_all_promoters, add_promoter, update_promoter, delete_promoter,
    find_active_promoter_by_phone,
    seed_coordinators, get_all_coordinators, add_coordinator, update_coordinator, delete_coordinator,
    find_active_coordinator_by_phone,
    get_all_administrators, add_administrator, update_administrator, delete_administrator,
    find_active_administrator_by_phone,
    is_first_session_of_day
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_backend")

# Define storage directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

GOALS_FILE = os.path.join(UPLOAD_DIR, "goals.json")
DISTRIBUTION_FILE = os.path.join(UPLOAD_DIR, "distribution.json")

# In-memory stores
goals_store = {}  # {product_name_or_file: [records]}
distribution_store = []  # [records]

# Load persisted data on start
if os.path.exists(GOALS_FILE):
    try:
        with open(GOALS_FILE, "r", encoding="utf-8") as f:
            goals_store = json.load(f)
        logger.info(f"Loaded persisted goals for products: {list(goals_store.keys())}")
    except Exception as e:
        logger.error(f"Error loading goals file: {e}")

if os.path.exists(DISTRIBUTION_FILE):
    try:
        with open(DISTRIBUTION_FILE, "r", encoding="utf-8") as f:
            distribution_store = json.load(f)
        logger.info(f"Loaded {len(distribution_store)} persisted distribution records.")
    except Exception as e:
        logger.error(f"Error loading distribution file: {e}")

app = FastAPI(
    title="Dashboard Ventas por Hora",
    description="Backend API para dashboard de ventas por hora con Oracle y Excels",
    version="1.0"
)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Login local (solución temporal — sin JWT, cookies ni micro de autenticación).
# Solo valida el usuario y contraseña quemados en backend/login/service.py.
# ---------------------------------------------------------------------------
@app.post("/api/login")
def login(email: str = Form(...), password: str = Form(...)):
    return login_service.login(email=email, password=password)

@app.post("/api/logout")
def logout():
    # Sin token ni cookies: el cliente limpia su bandera de sesión localmente.
    return {"message": "Sesión cerrada correctamente"}

# Helper: Convert oracle rows to dict list
def rows_to_dicts(cursor):
    columns = [col[0] for col in cursor.description]
    results = []
    for row in cursor.fetchall():
        row_dict = {}
        for col_name, val in zip(columns, row):
            # Format datetime objects as strings
            if isinstance(val, (datetime, date)):
                row_dict[col_name] = val.isoformat()
            elif isinstance(val, (bytes, bytearray)):
                # Columnas binarias (RAW/GUID/BLOB): representar como hex para evitar
                # fallos de serialización JSON (UnicodeDecodeError).
                row_dict[col_name] = bytes(val).hex()
            else:
                row_dict[col_name] = val
        results.append(row_dict)
    return results

# Helper: Generate realistic mock sales for demo fallback
def generate_mock_sales(desde_str: str, hasta_str: str):
    logger.info("Generating realistic mock sales data...")
    try:
        desde = datetime.strptime(desde_str, "%Y-%m-%d %H:%M:%S")
        hasta = datetime.strptime(hasta_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        desde = datetime.now() - timedelta(days=1)
        hasta = datetime.now()

    # Get offices/sites from loaded metas or use defaults
    sites = []
    if goals_store:
        # Extract distinct sites
        seen = set()
        for prod_goals in goals_store.values():
            for g in prod_goals:
                if g["cod_sitio"] not in seen:
                    seen.add(g["cod_sitio"])
                    sites.append({
                        "Cod_Sitio": g["cod_sitio"],
                        "Sitio_Venta": g["sitio_venta"],
                        "Cod_Oficina": g["cod_oficina"]
                    })
    
    # Cap unique sites in mock generator to avoid generating massive datasets that freeze the PC
    if len(sites) > 50:
        logger.info(f"Capping mock sites from {len(sites)} to 50 for performance safety.")
        sites = sites[:50]
    
    if not sites:
        # Default mock sites
        sites = [
            {"Cod_Sitio": 5006, "Sitio_Venta": "Antes De Llegar Al Puente", "Cod_Oficina": 5},
            {"Cod_Sitio": 5001, "Sitio_Venta": "Of El Terminal - Timba", "Cod_Oficina": 5},
            {"Cod_Sitio": 507901, "Sitio_Venta": "Movil Portales", "Cod_Oficina": 507},
            {"Cod_Sitio": 9026, "Sitio_Venta": "TAT Duvan El Pital", "Cod_Oficina": 9},
            {"Cod_Sitio": 4037, "Sitio_Venta": "TAT Duvan Monterilla Santander", "Cod_Oficina": 4}
        ]

    products = [
        {"Cod_Producto": 5, "Producto": "SUPER ASTRO"},
        {"Cod_Producto": 22005, "Producto": "TRANSACCIONES CNB"},
        {"Cod_Producto": 22069, "Producto": "CHANCE RASPA"},
        {"Cod_Producto": 13, "Producto": "GIROS CREADOS"},
        {"Cod_Producto": 17287, "Producto": "BET PLAY"}
    ]

    import random
    random.seed(42) # Consistent mock values

    mock_records = []
    current_day = desde
    while current_day < hasta:
        # Loop business hours (7 AM to 9 PM)
        for hour in range(7, 22):
            hour_str = f"{hour:02d}:00:00"
            dt_hour = current_day.replace(hour=hour, minute=0, second=0)
            
            for site in sites:
                # Randomize active products for this site and hour
                for prod in products:
                    if random.random() > 0.4:  # 60% chance of sale in this slot
                        base_val = 15000 if prod["Cod_Producto"] == 22005 else 50000
                        # Hour curve: higher sales at noon and 6 PM
                        hour_multiplier = 1.5 if (11 <= hour <= 13 or 17 <= hour <= 19) else 0.8
                        sale = round(random.randint(1000, 150000) * hour_multiplier, 2)
                        
                        mock_records.append({
                            "Cod_Sitio": site["Cod_Sitio"],
                            "Fecha": dt_hour.strftime("%Y-%m-%dT%H:00:00"),
                            "Cod_Producto": prod["Cod_Producto"],
                            "Fecha_Dia": current_day.strftime("%Y-%m-%dT00:00:00"),
                            "Hora": hour_str,
                            "Venta_Neta": sale
                        })
        current_day += timedelta(days=1)
        
    return mock_records

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up FastAPI application...")
    try:
        init_cache_db()
        seed_promoters_from_excel()
        seed_coordinators()
        db_manager.init_pools()
    except Exception as e:
        logger.error(f"Database pools / cache initialization error: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down FastAPI application...")
    db_manager.close_pools()

@app.get("/api/status")
def get_status():
    # On-demand check/retry to initialize pools if VPN or network was restored
    if not db_manager.pool_cauca or not db_manager.pool_fortuna:
        try:
            db_manager.init_pools()
        except Exception as e:
            logger.error(f"Status check connection pools auto-retry failed: {e}")
            
    cauca_ok = False
    if db_manager.pool_cauca:
        try:
            with db_manager.get_cauca_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM dual")
                    cauca_ok = True
        except Exception as e:
            logger.error(f"CAUCAMED connectivity check failed: {e}")

    fortuna_ok = False
    if db_manager.pool_fortuna:
        try:
            with db_manager.get_fortuna_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM dual")
                    fortuna_ok = True
        except Exception as e:
            logger.error(f"FORTUMED connectivity check failed: {e}")

    return {
        "cauca_connected": cauca_ok,
        "fortuna_connected": fortuna_ok,
        "goals_uploaded_products": [p for p, recs in goals_store.items() if recs and recs[0].get("activo", True)],
        "all_goals_products": list(goals_store.keys()),
        "distribution_records_count": len(distribution_store),
        "assistant_lock_enabled": ASSISTANT_LOCK_ENABLED,
    }


class AssistantUnlockRequest(BaseModel):
    password: str


@app.post("/api/assistant/unlock")
def assistant_unlock(req: AssistantUnlockRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Valida la contraseña del candado del Asistente contra el .env.

    La comparación ocurre solo en el servidor; el JS del navegador nunca conoce
    la clave. Si el candado está desactivado, se considera desbloqueado.
    """
    if not ASSISTANT_LOCK_ENABLED:
        return {"ok": True, "locked": False}
    if req.password == ASSISTANT_LOCK_PASSWORD:
        return {"ok": True, "locked": False}
    raise HTTPException(status_code=401, detail="Contraseña incorrecta")

@app.get("/api/ventas")
def get_ventas(
    desde: str = Query(..., description="Fecha inicio YYYY-MM-DD HH:MM:SS"),
    hasta: str = Query(..., description="Fecha fin YYYY-MM-DD HH:MM:SS"),
    force_refresh: bool = Query(False, description="Forzar consulta a Oracle y refrescar caché"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Executes the main hourly sales query on CAUCAMED and FORTUMED.
    Uses SQLite database for local caching to reduce load on Oracle and load instantly.
    If database queries fail but cache is present, falls back to cache.
    """
    cache_key = f"{desde}_{hasta}"
    
    # Helper to normalize OWO / APP sites
    def normalize_sale_records(records):
        if not records:
            return
        for r in records:
            site_code = r.get("Cod_Sitio")
            if site_code is not None:
                try:
                    site_code_int = int(site_code)
                    if site_code_int == 136033:
                        r["Cod_Sitio"] = 333033
                    elif site_code_int == 136034:
                        r["Cod_Sitio"] = 334034
                except:
                    pass

    # 1. Check local SQLite cache first if not forcing refresh
    cached_data, last_updated = get_cached_sales(cache_key)
    
    if cached_data is not None and not force_refresh:
        # Check if the cache has expired (only for TODAY, historical data NEVER expires)
        today_str = date.today().strftime("%Y-%m-%d")
        yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        is_today = desde.startswith(today_str)
        is_yesterday = desde.startswith(yesterday_str)
        
        cache_valid = True
        
        # Auto-expire yesterday's cache if it was created BEFORE today (e.g., missing final closing data at 20:00)
        # This ensures the first request on the next day fetches the definitive Oracle data.
        # UPDATE: User requested to ALWAYS use SQLite for yesterday to avoid long Oracle query times.
        # if is_yesterday:
        #     try:
        #         dt_updated = datetime.fromisoformat(last_updated)
        #         if dt_updated.date() < date.today():
        #             cache_valid = False
        #     except Exception:
        #         pass
                
        # Expiration check disabled temporarily by user request
        # if is_today:
        #     try:
        #         dt_updated = datetime.fromisoformat(last_updated)
        #         # Expire after 1 hour
        #         if datetime.now() - dt_updated > timedelta(hours=1):
        #             cache_valid = False
        #     except Exception:
        #         cache_valid = False
        
        if cache_valid:
            logger.info(f"Serving sales data from SQLite Cache for key {cache_key} (updated: {last_updated}).")
            normalize_sale_records(cached_data)
            return {
                "source": "LOCAL_CACHE",
                "last_updated": last_updated,
                "data": cached_data
            }
        else:
            logger.info(f"Cache expired for today's key {cache_key}. Proceeding to query Oracle...")
            
    # 2. Query Databases
    logger.info(f"Fetching sales from Oracle databases: {desde} to {hasta}")
    
    results = []
    errors = []
    db_failures = False

    # Query CAUCAMED
    if db_manager.pool_cauca:
        try:
            with db_manager.get_cauca_connection() as conn:
                with conn.cursor() as cursor:
                    logger.info("Executing main query on CAUCAMED...")
                    cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                    cauca_res = rows_to_dicts(cursor)
                    # Tag source
                    for r in cauca_res:
                        r["Fuente"] = "CAUCA"
                    results.extend(cauca_res)
                    logger.info(f"Retrieved {len(cauca_res)} rows from CAUCAMED.")
        except Exception as e:
            msg = f"CAUCAMED query failed: {e}"
            logger.error(msg)
            errors.append(msg)
            db_failures = True
    else:
        errors.append("CAUCAMED pool not initialized.")
        db_failures = True

    # Query FORTUMED
    if db_manager.pool_fortuna:
        try:
            with db_manager.get_fortuna_connection() as conn:
                with conn.cursor() as cursor:
                    logger.info("Executing main query on FORTUMED...")
                    cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                    fortuna_res = rows_to_dicts(cursor)
                    # Tag source
                    for r in fortuna_res:
                        r["Fuente"] = "FORTUNA"
                    results.extend(fortuna_res)
                    logger.info(f"Retrieved {len(fortuna_res)} rows from FORTUMED.")
        except Exception as e:
            msg = f"FORTUMED query failed: {e}"
            logger.error(msg)
            errors.append(msg)
            db_failures = True
    else:
        errors.append("FORTUMED pool not initialized.")
        db_failures = True

    # Normalize the fresh database results
    normalize_sale_records(results)

    # 3. Fallback to cache if database fails/is incomplete but we have stale cache
    if (db_failures or not results) and cached_data is not None:
        logger.warning(f"Database query failed or is incomplete. Errors: {errors}. Serving stale SQLite Cache.")
        normalize_sale_records(cached_data)
        return {
            "source": "LOCAL_CACHE_STALE",
            "last_updated": last_updated,
            "data": cached_data,
            "warning": f"Error de conexión con base de datos. Mostrando caché anterior. Errores: {', '.join(errors)}"
        }

    # Fallback to mock data if database failed and no cache is available
    if db_failures or not results:
        logger.warning(f"Database query failed and no SQLite Cache is available. Falling back to Mock Sales generation.")
        try:
            results = generate_mock_sales(desde, hasta)
            set_cached_sales(cache_key, results)
            now_str = datetime.now().isoformat()
            return {
                "source": "MOCK_FALLBACK",
                "last_updated": now_str,
                "data": results,
                "warning": f"Conexión a Oracle no disponible. Mostrando datos simulados (Mock). Errores: {', '.join(errors)}"
            }
        except Exception as mock_err:
            logger.error(f"Failed to generate mock sales: {mock_err}")
            logger.error(f"Failed to query Oracle databases. Errors: {errors}")
            raise HTTPException(
                status_code=503,
                detail=f"Error de conexión con Oracle: No se pudo establecer conexión con las bases de datos (CAUCAMED/FORTUMED). Verifica tu VPN e inténtalo de nuevo."
            )

    # 4. Save successful results to cache
    set_cached_sales(cache_key, results)
    
    # Return fresh results
    now_str = datetime.now().isoformat()
    return {
        "source": "REAL_DATABASE",
        "last_updated": now_str,
        "data": results
    }

@app.api_route("/api/ventas/refresh", methods=["GET", "POST"])
def force_refresh_ventas(
    background_tasks: BackgroundTasks,
    desde: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD HH:MM:SS"),
    hasta: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD HH:MM:SS")
):
    """
    Endpoint for external schedulers (like n8n) to force update the SQLite cache.
    Runs in background to prevent timeout issues (takes 5+ mins for all queries).
    """
    def _run_refreshes(_desde, _hasta):
        logger.info("Starting background refresh tasks...")
        try:
            if _desde and _hasta and _desde != "AUTO":
                # Specific range requested
                get_ventas(desde=_desde, hasta=_hasta, force_refresh=True)
                return

            # Auto mode (no params) -> Refresh Everything
            today_str = datetime.now().strftime("%Y-%m-%d")
            tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            month_start = f"{today_str[:7]}-01 00:00:00"
            
            # 1. Update Yesterday's Cache
            logger.info(f"Background: Auto-refreshing Yesterday's Cache")
            get_ventas(desde=f"{yesterday_str} 00:00:00", hasta=f"{yesterday_str} 23:59:59", force_refresh=True)
            
            # 2. Update Monthly Cache (used by WhatsApp 'Mensual' metric)
            logger.info(f"Background: Auto-refreshing Monthly Cache")
            get_ventas(desde=month_start, hasta=f"{today_str} 23:59:59", force_refresh=True)
            
            # 3. Update Today's Cache
            logger.info(f"Background: Auto-refreshing Today's Cache")
            get_ventas(desde=f"{today_str} 00:00:00", hasta=f"{today_str} 23:59:59", force_refresh=True)
            
            # 4. Update Betplay Pagos & Recargas
            logger.info(f"Background: Auto-refreshing Betplay")
            compute_betplay_resumen("pagos", desde=f"{today_str} 00:00:00", hasta=f"{tomorrow_str} 00:00:00", force_refresh=True)
            compute_betplay_resumen("recargas", desde=f"{today_str} 00:00:00", hasta=f"{tomorrow_str} 00:00:00", force_refresh=True)
            
            logger.info("Background refresh tasks completed successfully.")
        except Exception as e:
            logger.error(f"Background refresh failed: {e}")

    # Launch in background
    _d = desde or "AUTO"
    _h = hasta or "AUTO"
    background_tasks.add_task(_run_refreshes, _d, _h)
    
    return {
        "status": "refreshing_in_background",
        "message": "Las actualizaciones de caché (Ayer, Mes, Hoy y Betplay) se han iniciado en segundo plano.",
        "desde": _d,
        "hasta": _h
    }


# Pydantic models for WhatsApp Promoters
class PromoterSchema(BaseModel):
    name: str
    zone: str
    phone: str
    active: int = 1

@app.get("/api/whatsapp-promoters")
def get_whatsapp_promoters_endpoint(current_user: CurrentUser = Depends(get_current_user)):
    """
    Returns list of all promoters in the whatsapp_promoters table.
    """
    return get_all_promoters()

@app.post("/api/whatsapp-promoters")
def create_whatsapp_promoter(p: PromoterSchema, current_user: CurrentUser = Depends(get_current_user)):
    """
    Adds a new promoter to the database.
    """
    try:
        pid = add_promoter(p.name, p.zone, p.phone, p.active)
        return {"id": pid, "status": "success", "message": f"Promotor {p.name} agregado."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al agregar promotor.")

@app.put("/api/whatsapp-promoters/{pid}")
def update_whatsapp_promoter(pid: int, p: PromoterSchema, current_user: CurrentUser = Depends(get_current_user)):
    """
    Updates an existing promoter in the database.
    """
    try:
        success = update_promoter(pid, p.name, p.zone, p.phone, p.active)
        if not success:
            raise HTTPException(status_code=404, detail="Promotor no encontrado.")
        return {"status": "success", "message": f"Promotor {p.name} actualizado."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al actualizar promotor.")

@app.delete("/api/whatsapp-promoters/{pid}")
def delete_whatsapp_promoter(pid: int, current_user: CurrentUser = Depends(get_current_user)):
    """
    Deletes a promoter from the database.
    """
    success = delete_promoter(pid)
    if not success:
        raise HTTPException(status_code=404, detail="Promotor no encontrado.")
    return {"status": "success", "message": "Promotor eliminado."}


# Pydantic models for WhatsApp Coordinators
class CoordinatorSchema(BaseModel):
    name: str
    cedula: str
    role: str
    zone: str
    phone: str
    active: int = 1

class AdministratorSchema(BaseModel):
    name: str
    cedula: str
    phone: str
    active: int = 1

@app.get("/api/whatsapp-administrators")
def get_whatsapp_administrators_endpoint(current_user: CurrentUser = Depends(get_current_user)):
    """
    Returns list of all administrators in the whatsapp_administrators table.
    """
    return get_all_administrators()

@app.post("/api/whatsapp-administrators")
def create_whatsapp_administrator(a: AdministratorSchema, current_user: CurrentUser = Depends(get_current_user)):
    """
    Adds a new administrator to the database.
    """
    try:
        aid = add_administrator(a.name, a.cedula, a.phone, a.active)
        return {"id": aid, "status": "success", "message": f"Administrador {a.name} agregado."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al agregar administrador.")

@app.put("/api/whatsapp-administrators/{aid}")
def update_whatsapp_administrator(aid: int, a: AdministratorSchema, current_user: CurrentUser = Depends(get_current_user)):
    """
    Updates an existing administrator in the database.
    """
    try:
        success = update_administrator(aid, a.name, a.cedula, a.phone, a.active)
        if not success:
            raise HTTPException(status_code=404, detail="Administrador no encontrado.")
        return {"status": "success", "message": f"Administrador {a.name} actualizado."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al actualizar administrador.")

@app.delete("/api/whatsapp-administrators/{aid}")
def delete_whatsapp_administrator(aid: int, current_user: CurrentUser = Depends(get_current_user)):
    """
    Deletes an administrator from the database.
    """
    success = delete_administrator(aid)
    if not success:
        raise HTTPException(status_code=404, detail="Administrador no encontrado.")
    return {"status": "success", "message": "Administrador eliminado."}

@app.get("/api/whatsapp-coordinators")
def get_whatsapp_coordinators_endpoint(current_user: CurrentUser = Depends(get_current_user)):
    """
    Returns list of all coordinators in the whatsapp_coordinators table.
    """
    return get_all_coordinators()

@app.post("/api/whatsapp-coordinators")
def create_whatsapp_coordinator(c: CoordinatorSchema, current_user: CurrentUser = Depends(get_current_user)):
    """
    Adds a new coordinator to the database.
    """
    try:
        cid = add_coordinator(c.name, c.cedula, c.role, c.zone, c.phone, c.active)
        return {"id": cid, "status": "success", "message": f"Coordinador {c.name} agregado."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al agregar coordinador.")

@app.put("/api/whatsapp-coordinators/{cid}")
def update_whatsapp_coordinator(cid: int, c: CoordinatorSchema, current_user: CurrentUser = Depends(get_current_user)):
    """
    Updates an existing coordinator in the database.
    """
    try:
        success = update_coordinator(cid, c.name, c.cedula, c.role, c.zone, c.phone, c.active)
        if not success:
            raise HTTPException(status_code=404, detail="Coordinador no encontrado.")
        return {"status": "success", "message": f"Coordinador {c.name} actualizado."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno al actualizar coordinador.")

@app.delete("/api/whatsapp-coordinators/{cid}")
def delete_whatsapp_coordinator(cid: int, current_user: CurrentUser = Depends(get_current_user)):
    """
    Deletes a coordinator from the database.
    """
    success = delete_coordinator(cid)
    if not success:
        raise HTTPException(status_code=404, detail="Coordinador no encontrado.")
    return {"status": "success", "message": "Coordinador eliminado."}

TABLA_TO_PRODUCT_NAME = {
    'SIGT_CHANCES':              'CHANCE',
    'SIGT_CHANCES_RASPA':        'RASPITA',
    'SIGT_DOBLE_GANA':           'DOBLE CHANCE',
    'SIGT_SUPER_ASTRO':          'SUPER ASTRO',
    'SIGT_BALOTO':               'BALOTO',
    'SIGT_RECARGAS':             'RECARGA EN LINEA',
    'SIGT_SG_GIROS_CREADOS':     'GIROS',
    'SIGT_SG_GIROS_PAGADOS':     'GIROS',
    'SIGT_LOTERIAS_LINEA':       'LOTERIA EN LINEA',
    'SIGT_RECAUDOS_EMPRESAS':    'RECAUDOS EMPRESARIALES',
    'SIGT_VENTA_INCENTIVO_COBRO':'TRANSACCIONES CNB',
}

COD_TO_PRODUCT_NAME = {
    5: 'SUPER ASTRO',
    22005: 'TRANSACCIONES CNB',
    22069: 'RASPITA',
    22059: 'BALOTO',
    22070: 'MILOTO',
    22075: 'COLOR LOTO',
}

SPECIAL_PRODUCTS = [
    { "key": "BET PLAY", "patterns": ["BETPLAY", "BET PLAY", "BTP"] },
    { "key": "PATA MILLONARIA", "patterns": ["PATA MILLONARIA", "PT"] },
    { "key": "DOBLE CHANCE", "patterns": ["3C DOBLE CH REGIONAL", "4C DOBLE CH REGIONAL", "DOBLE CHANCE", "DOBLE GANA", "DOBLE CH", "DDCH"] },
    { "key": "BILLONARIO NACIONAL", "patterns": ["BILLONARIO", "BILLONARIO NACIONAL"] },
    { "key": "CHANCE MILLONARIO", "patterns": ["CHANCE MILLONARIO", "CHML"] },
    { "key": "COLOR LOTO", "patterns": ["COLOR LOTO", "CLOT"] },
    { "key": "MILOTO", "patterns": ["MILOTO", "MLT"] },
    { "key": "BALOTO", "patterns": ["BALOTO", "BLT", "BLL"] },
    { "key": "LOTERIA EN LINEA", "patterns": ["LOTERIA EN LINEA", "LOT", "LOTE", "RYL"] },
    { "key": "GIROS", "patterns": ["GIROS", "GIRO", "ENVIO GIRO"] }
]

def get_special_product_key(product_name):
    if not product_name:
        return None
    name = str(product_name).strip().replace("*", "").upper()
    for spec in SPECIAL_PRODUCTS:
        for pat in spec["patterns"]:
            if pat in name or name == pat:
                return spec["key"]
    return None

def normalize_product(raw_name):
    if not raw_name:
        return "OTROS"
    name = str(raw_name).strip().replace("*", "").upper()
    
    spec_key = get_special_product_key(name)
    if spec_key:
        return spec_key
        
    if name.startswith("CHON") or name.startswith("CHOD") or name.startswith("BOGO") or name.startswith("CHO"):
        return "CHANCE"
    if "CHANCE" in name or name == "CH":
        return "CHANCE"
    if "SUPER ASTRO" in name or "ASTRO" in name or name == "SA":
        return "SUPER ASTRO"
    if "GIROS" in name or name == "GIROS":
        return "GIROS"
    if "RECARGA" in name or name == "RC":
        return "RECARGA EN LINEA"
    if "TRANSACCIONES CNB" in name or "CNB" in name or name == "TRCNB":
        return "TRANSACCIONES CNB"
    if "RECAUDOS EMPRESARIALES" in name or "RECAUDOS" in name or name == "RCDEM":
        return "RECAUDOS EMPRESARIALES"
    if "LOTERIAS" in name or "LOTERIA" in name or name == "LOT":
        return "LOTERIA EN LINEA"
    if "RASPAS" in name or "RASPA" in name or name == "RASPITA" or name == "RYL":
        return "RASPITA"
    if "BALOTO" in name or name == "BALOTO":
        return "BALOTO"
    if "MILOTO" in name or name == "MILOTO":
        return "MILOTO"
    if "COLOR LOTO" in name or name == "COLORLOTO":
        return "COLOR LOTO"
    if "PATA MILLONARIA" in name or name == "PATA":
        return "PATA MILLONARIA"
        
    return "OTROS"

def resolve_product_name(sale, products_by_code=None):
    cod_prod = sale.get("Cod_Producto")
    if cod_prod is not None:
        cod_prod_str = str(cod_prod)
        if products_by_code and cod_prod_str in products_by_code:
            prod_info = products_by_code[cod_prod_str]
            prod_name = prod_info.get("Producto")
            prod_type = prod_info.get("Tipo_Producto") or prod_info.get("Tipo Producto")
            spec_key = get_special_product_key(prod_name)
            if spec_key:
                return spec_key
            return normalize_product(prod_type or prod_name)
            
        # Hardcoded fallback if catalog not loaded
        code_map = {
            22059: "BALOTO",
            22070: "MILOTO",
            22075: "COLOR LOTO",
            22069: "RASPITA",
            5: "SUPER ASTRO",
            22005: "TRANSACCIONES CNB",
            17287: "BET PLAY",
            17288: "BET PLAY",
            21931: "BET PLAY",
            21972: "BET PLAY"
        }
        try:
            cod_prod_int = int(cod_prod)
            if cod_prod_int in code_map:
                return code_map[cod_prod_int]
        except:
            pass
            
    src_table = sale.get("Tabla_Origen")
    if src_table and src_table in TABLA_TO_PRODUCT_NAME:
        return TABLA_TO_PRODUCT_NAME[src_table]
            
    return "OTROS"

@app.get("/api/whatsapp/query")
def get_whatsapp_query(
    phone: Optional[str] = Query(None, description="Número de celular del promotor o coordinador"),
    report_type: str = Query("products", description="Tipo de reporte: 'products', 'offices', 'prompt_product', o 'product_office'"),
    selected_product: Optional[str] = Query(None, description="Producto seleccionado para reporte producto/oficina"),
    override_promoter_name: Optional[str] = Query(None, description="Nombre de promotor para consulta por coordinador"),
    override_coordinator_name: Optional[str] = Query(None, description="Nombre de coordinador para consulta por administrador"),
    ref_date: Optional[str] = Query(None, description="Fecha de referencia YYYY-MM-DD; por defecto hoy. Usada para el reporte de 'ayer'."),
    current_user: CurrentUser = Depends(get_current_user),
):
    # Resolve FastAPI Query defaults if called directly in Python
    if not isinstance(selected_product, str):
        selected_product = None
    if not isinstance(override_promoter_name, str):
        override_promoter_name = None
    if not isinstance(override_coordinator_name, str):
        override_coordinator_name = None
    if not isinstance(phone, str):
        phone = None
    if not isinstance(report_type, str):
        report_type = "products"



    # Fecha de referencia del reporte: hoy por defecto, o la indicada (ej. ayer).
    real_today = datetime.now().strftime("%Y-%m-%d")
    if isinstance(ref_date, str) and ref_date.strip():
        report_date = ref_date.strip()
    else:
        report_date = real_today
    is_past_day = report_date != real_today

    # 1. Buscar promotor, coordinador o administrador por celular
    is_administrator = False
    is_coordinator = False
    
    if override_promoter_name:
        user_name = override_promoter_name
        is_coordinator = False
        user_label = "Promotor"
        # Find zone for this promoter
        user_zone = "Sin Zona"
        for item in distribution_store:
            if item.get("promotor") and str(item["promotor"]).strip().lower() == user_name.strip().lower():
                user_zone = item.get("zona", "Sin Zona")
                break
    elif override_coordinator_name:
        user_name = override_coordinator_name
        is_coordinator = True
        user_label = "Coordinador"
        from backend.cache import get_all_coordinators
        coors = get_all_coordinators()
        user_zone = "Sin Zona"
        for c in coors:
            if c["name"].strip().lower() == user_name.strip().lower():
                user_zone = c["zone"]
                break
    else:
        if not phone:
            return {"text": "❌ Falta número de teléfono o nombre para la consulta."}
        
        administrator = find_active_administrator_by_phone(phone)
        promoter = None
        coordinator = None
        if not administrator:
            promoter = find_active_promoter_by_phone(phone)
            if not promoter:
                coordinator = find_active_coordinator_by_phone(phone)
                
        if not administrator and not promoter and not coordinator:
            return {
                "text": "❌ Lo sentimos, tu número de celular no está registrado o no se encuentra activo para consultas por WhatsApp."
            }
            
        if administrator:
            user_name = administrator["name"]
            is_administrator = True
            user_label = "Administrador"
            user_zone = "Nivel Nacional"
        elif promoter:
            user_name = promoter["name"]
            is_coordinator = False
            user_label = "Promotor"
            user_zone = promoter["zone"]
        else:
            user_name = coordinator["name"]
            is_coordinator = True
            user_label = "Coordinador"
            user_zone = coordinator["zone"]

    # 2. Encontrar oficinas asignadas en la distribución comercial
    assigned_offices = set()
    if is_administrator:
        # Administrators see all offices
        for item in distribution_store:
            if item.get("cod_oficina") is not None:
                try:
                    assigned_offices.add(int(item["cod_oficina"]))
                except:
                    pass
    elif is_coordinator:
        for item in distribution_store:
            item_zone = item.get("zona", "")
            
            match_zone = False
            is_yudy = "yud" in user_name.strip().lower() or "moral" in user_name.strip().lower() or "oriente y municipios centro" in user_zone.strip().lower()
            if is_yudy:
                item_z_lower = str(item_zone).strip().lower()
                if item_z_lower in ["oriente y municipios centro", "centro", "municipios centro", "zona centro", "oriente"]:
                    match_zone = True
                elif "centro" in item_z_lower or "oriente" in item_z_lower:
                    match_zone = True
            else:
                if item_zone and str(item_zone).strip().lower() == user_zone.strip().lower():
                    match_zone = True
                    
            if match_zone:
                if item.get("cod_oficina") is not None:
                    try:
                        assigned_offices.add(int(item["cod_oficina"]))
                    except:
                        pass
    else:
        for item in distribution_store:
            item_promotor = item.get("promotor", "")
            if item_promotor and str(item_promotor).strip().lower() == user_name.strip().lower():
                if item.get("cod_oficina") is not None:
                    try:
                        assigned_offices.add(int(item["cod_oficina"]))
                    except:
                        pass
                    
    if not assigned_offices:
        detail_msg = f"coordinador de la zona {user_zone}" if is_coordinator else "promotor"
        return {
            "text": f"⚠️ Hola {user_name}, estás registrado en WhatsApp como {detail_msg} pero no tienes oficinas asignadas en la distribución comercial cargada."
        }

    # Calculate coordinator summary list for administrators
    coor_compliance_list = []
    if is_administrator and report_type in {"products", "coordinators"}:
        from backend.cache import get_all_coordinators
        all_coors = get_all_coordinators()
        active_coors = [c for c in all_coors if c.get("active", 1)]
        
        # Site to office mapping
        sites_data, _ = get_cached_sales("catalog_sitios")
        site_to_office_local = {}
        if sites_data:
            for s in sites_data:
                s_code = s.get("Cod_Sitio")
                off_code = s.get("Cod_Oficina")
                if s_code is not None and off_code is not None:
                    site_to_office_local[int(s_code)] = int(off_code)
        site_to_office_local[333033] = 333
        site_to_office_local[334034] = 334
        
        today_str = report_date
        sales_list_local = []
        try:
            sales_resp_local = get_ventas(desde=f"{today_str} 00:00:00", hasta=f"{today_str} 23:59:59", force_refresh=False)
            sales_list_local = sales_resp_local.get("data", [])
        except:
            pass
            
        for c in active_coors:
            c_name = c["name"]
            c_zone = c["zone"]
            
            c_offices = set()
            for item in distribution_store:
                item_zone = item.get("zona", "")
                
                match_zone = False
                is_yudy_admin = "yud" in c_name.strip().lower() or "moral" in c_name.strip().lower() or "oriente y municipios centro" in c_zone.strip().lower()
                if is_yudy_admin:
                    item_z_lower = str(item_zone).strip().lower()
                    if item_z_lower in ["oriente y municipios centro", "centro", "municipios centro", "zona centro", "oriente"]:
                        match_zone = True
                    elif "centro" in item_z_lower or "oriente" in item_z_lower:
                        match_zone = True
                else:
                    if item_zone and item_zone.strip().lower() == c_zone.strip().lower():
                        match_zone = True
                        
                if match_zone:
                    if item.get("cod_oficina") is not None:
                        try:
                            c_offices.add(int(item["cod_oficina"]))
                        except:
                            pass
            
            c_sales = 0.0
            for sale in sales_list_local:
                src_table = sale.get("Tabla_Origen")
                if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
                    continue
                s_code = sale.get("Cod_Sitio")
                if s_code is not None:
                    try:
                        s_code_int = int(s_code)
                        off_code = site_to_office_local.get(s_code_int)
                        if off_code in c_offices:
                            c_sales += float(sale.get("Venta_Neta") or 0.0)
                    except:
                        pass
                        
            c_meta = 0.0
            for prod_name, records in goals_store.items():
                if records and not records[0].get("activo", True):
                    continue
                for rec in records:
                    if rec.get("fecha") == today_str:
                        off_code = rec.get("cod_oficina")
                        if off_code is not None:
                            try:
                                off_code_int = int(off_code)
                                if off_code_int in c_offices:
                                    meta_val = float(rec.get("meta") or 0.0)
                                    if prod_name in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}:
                                        meta_val = float(round(meta_val))
                                    c_meta += meta_val
                            except:
                                pass
                                
            if c_meta > 0:
                c_comp = (c_sales / c_meta * 100.0)
            else:
                c_comp = 100.0 if c_sales > 0 else 0.0
                
            coor_compliance_list.append((c_name, c_zone, c_sales, c_meta, c_comp))
        coor_compliance_list.sort(key=lambda x: x[0])

    # Calculate individual promoter metrics in coordinator's zone
    promoter_compliance_list = []
    if is_coordinator and report_type in {"products", "offices", "prompt_promoter", "coordinator_promoter_detail"}:
        promoter_to_offices = {}
        promoter_zones = {}
        for item in distribution_store:
            item_zone = item.get("zona", "")
            
            match_zone = False
            is_yudy = "yud" in user_name.strip().lower() or "moral" in user_name.strip().lower() or "oriente y municipios centro" in user_zone.strip().lower()
            if is_yudy:
                item_z_lower = str(item_zone).strip().lower()
                if item_z_lower in ["oriente y municipios centro", "centro", "municipios centro", "zona centro", "oriente"]:
                    match_zone = True
                elif "centro" in item_z_lower or "oriente" in item_z_lower:
                    match_zone = True
            else:
                if item_zone and item_zone.strip().lower() == user_zone.strip().lower():
                    match_zone = True
                    
            if match_zone:
                p_name = item.get("promotor")
                off = item.get("cod_oficina")
                if p_name and off is not None:
                    try:
                        off_int = int(off)
                        if p_name not in promoter_to_offices:
                            promoter_to_offices[p_name] = set()
                        promoter_to_offices[p_name].add(off_int)
                        item_z_lower = str(item_zone).strip().lower()
                        if "centro" in item_z_lower and "oriente" not in item_z_lower:
                            promoter_zones[p_name] = "Centro"
                        else:
                            promoter_zones[p_name] = "Oriente"
                    except:
                        pass
                        
        sites_data, _ = get_cached_sales("catalog_sitios")
        site_to_office = {}
        if sites_data:
            for s in sites_data:
                s_code = s.get("Cod_Sitio")
                off_code = s.get("Cod_Oficina")
                if s_code is not None and off_code is not None:
                    site_to_office[int(s_code)] = int(off_code)
        # Register OWO / APP sites manually to offices 333 / 334
        site_to_office[333033] = 333
        site_to_office[334034] = 334
                    
        products_data, _ = get_cached_sales("catalog_productos")
        products_by_code = {}
        if products_data:
            for p in products_data:
                cod = p.get("Cod_Producto")
                if cod is not None:
                    products_by_code[str(cod)] = p

        today_str = report_date
        desde = f"{today_str} 00:00:00"
        hasta = f"{today_str} 23:59:59"
        
        sales_list = []
        db_update_time_str = "Desconocida"
        try:
            sales_resp = get_ventas(desde=desde, hasta=hasta, force_refresh=False)
            sales_list = sales_resp.get("data", [])
            last_updated = sales_resp.get("last_updated")
            if last_updated:
                try:
                    from datetime import datetime as dt_class
                    dt = dt_class.fromisoformat(last_updated)
                    db_update_time_str = dt.strftime("%d/%m/%Y %I:%M %p")
                except:
                    db_update_time_str = str(last_updated)
        except:
            pass
            
        for p_name, p_offices in promoter_to_offices.items():
            p_sales = 0.0
            for sale in sales_list:
                src_table = sale.get("Tabla_Origen")
                s_code = sale.get("Cod_Producto")
                if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
                    continue
                s_code = sale.get("Cod_Sitio")
                if s_code is not None:
                    try:
                        s_code_int = int(s_code)
                        off_code = site_to_office.get(s_code_int)
                        if off_code in p_offices:
                            v_neta = float(sale.get("Venta_Neta") or 0.0)
                            p_sales += v_neta
                    except:
                        pass
                        
            p_meta = 0.0
            for prod_name, records in goals_store.items():
                if records and not records[0].get("activo", True):
                    continue
                for rec in records:
                    if rec.get("fecha") == today_str:
                        off_code = rec.get("cod_oficina")
                        if off_code is not None:
                            try:
                                off_code_int = int(off_code)
                                if off_code_int in p_offices:
                                    meta_val = float(rec.get("meta") or 0.0)
                                    if prod_name in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}:
                                        meta_val = float(round(meta_val))
                                    p_meta += meta_val
                            except:
                                pass
            if p_meta > 0:
                p_comp = (p_sales / p_meta * 100.0)
            else:
                p_comp = 100.0 if p_sales > 0 else 0.0
            promoter_compliance_list.append((p_name, p_sales, p_meta, p_comp, promoter_zones.get(p_name, "")))
            
        promoter_compliance_list.sort(key=lambda x: x[0])

    # Early return for coordinators summary for administrator
    if is_administrator and report_type == "coordinators":
        today_str = report_date
        db_update_time_str = "Desconocida"
        try:
            sales_resp = get_ventas(desde=f"{today_str} 00:00:00", hasta=f"{today_str} 23:59:59", force_refresh=False)
            last_updated = sales_resp.get("last_updated")
            if last_updated:
                try:
                    from datetime import datetime as dt_class
                    dt = dt_class.fromisoformat(last_updated)
                    db_update_time_str = dt.strftime("%d/%m/%Y %I:%M %p")
                except:
                    db_update_time_str = str(last_updated)
        except:
            pass
            
        if is_past_day:
            msg = f"👥 *CUMPLIMIENTO POR COORDINADOR (AYER)*\n"
        else:
            msg = f"👥 *CUMPLIMIENTO POR COORDINADOR*\n"
        msg += f"📅 *Fecha:* {today_str}\n"
        msg += f"🔄 *Actualizado DB:* {db_update_time_str}\n"
        msg += f"──────────────────\n"
        for i, (c_name, c_zone, c_sales, c_meta, c_comp) in enumerate(coor_compliance_list, 1):
            c_emoji = "🟢" if c_comp >= 95 else "🔴"
            c_faltante = max(0.0, c_meta - c_sales)
            msg += f"{i}. 👤 *{c_name}* ({c_zone}) ({c_emoji} *{c_comp:.1f}%*)\n"
            msg += f"  ↳ Venta: ${round(c_sales):,}\n"
            msg += f"  ↳ Meta: ${round(c_meta):,}\n"
            msg += f"  ↳ Faltante: ${round(c_faltante):,}\n\n"
            
        msg += f"──────────────────\n"
        msg += f"📲 Para ver el detalle por producto, responde con el número del coordinador (Ej: *1*)\n"
        msg += f"💪 ¡Vamos por la meta! 🚀"
        return {
            "text": msg,
            "report_type": "coordinators_summary",
            "is_administrator": True
        }

    # Early return for administrator looking at a specific coordinator's details
    if is_administrator and report_type == "administrator_coordinator_detail":
        if selected_product and selected_product.isdigit():
            idx = int(selected_product) - 1
            from backend.cache import get_all_coordinators
            all_coors = get_all_coordinators()
            active_coors_sorted = sorted([c for c in all_coors if c.get("active", 1)], key=lambda x: x["name"])
            if 0 <= idx < len(active_coors_sorted):
                selected_coord_name = active_coors_sorted[idx]["name"]
                # Recursively call the function as if the administrator is that coordinator requesting "products"
                result = get_whatsapp_query(
                    phone=None,
                    report_type="products",
                    selected_product=None,
                    override_promoter_name=None,
                    override_coordinator_name=selected_coord_name,
                    ref_date=ref_date,
                )
                result["is_administrator"] = True
                result["is_coordinator"] = False
                result["report_type"] = "administrator_coordinator_products_view"
                return result
            else:
                return {
                    "text": "❌ El número ingresado no corresponde a ningún coordinador de la lista.",
                    "report_type": "administrator_coordinator_detail",
                    "is_administrator": True
                }
        else:
            return {
                "text": "❌ Formato inválido. Por favor, responde únicamente con el número del coordinador.",
                "report_type": "administrator_coordinator_detail",
                "is_administrator": True
            }

    # Early return for prompt_promoter (promoter summary for coordinator)
    if is_coordinator and report_type == "prompt_promoter":
        if not promoter_compliance_list:
            return {
                "text": "⚠️ No hay promotores asignados a tu zona en la distribución comercial.",
                "report_type": "prompt_promoter",
                "is_coordinator": True
            }
        is_yudy = "yud" in user_name.strip().lower() or "moral" in user_name.strip().lower() or "oriente y municipios centro" in user_zone.strip().lower()
        if is_yudy:
            if is_past_day:
                msg = f"👥 *RESUMEN DE PROMOTORES (AYER) - ZONA: ORIENTE Y CENTRO*\n"
            else:
                msg = f"👥 *RESUMEN DE PROMOTORES (v4) - ZONA: ORIENTE Y CENTRO*\n"
            msg += f"📅 *Fecha:* {today_str}\n"
            msg += f"🔄 *Actualizado DB:* {db_update_time_str}\n"
            
            msg += f"\n---- promotores zona oriente ----\n"
            for (p_name, p_sales, p_meta, p_comp, p_zone) in promoter_compliance_list:
                if p_zone != "Centro":
                    p_emoji = "🟢" if p_comp >= 95 else "🔴"
                    p_faltante = max(0.0, p_meta - p_sales)
                    msg += f"• 👤 *{p_name}* ({p_emoji} *{p_comp:.1f}%*)\n"
                    msg += f"  ↳ Meta del Día: ${round(p_meta):,}\n"
                    msg += f"  ↳ Faltante Meta: ${round(p_faltante):,}\n\n"
                    
            msg += f"---- zona centro ----\n"
            for (p_name, p_sales, p_meta, p_comp, p_zone) in promoter_compliance_list:
                if p_zone == "Centro":
                    p_emoji = "🟢" if p_comp >= 95 else "🔴"
                    p_faltante = max(0.0, p_meta - p_sales)
                    msg += f"• 👤 *{p_name}* ({p_emoji} *{p_comp:.1f}%*)\n"
                    msg += f"  ↳ Meta del Día: ${round(p_meta):,}\n"
                    msg += f"  ↳ Faltante Meta: ${round(p_faltante):,}\n\n"
                    
            msg += f"──────────────────\n"
            msg += f"📲 Para ver el detalle por oficina, responde con el número del promotor (Ej: *1*)\n"
            msg += f"💪 ¡Vamos por la meta! 🚀"
        else:
            if is_past_day:
                msg = f"👥 *RESUMEN DE PROMOTORES (AYER) - ZONA: {user_zone}*\n"
            else:
                msg = f"👥 *RESUMEN DE PROMOTORES (Debug) - ZONA: {user_zone}*\n"
            msg += f"👤 *Coordinador:* {user_name}\n"
            msg += f"📅 *Fecha:* {today_str}\n"
            msg += f"🔄 *Actualizado DB:* {db_update_time_str}\n"
            msg += f"──────────────────\n"
            for idx, item in enumerate(promoter_compliance_list, 1):
                p_name, p_sales, p_meta, p_comp = item[:4]
                p_emoji = "🟢" if p_comp >= 95 else "🔴"
                p_faltante = max(0.0, p_meta - p_sales)
                msg += f"• 👤 *{p_name}* ({p_emoji} *{p_comp:.1f}%*)\n"
                msg += f"  ↳ Meta del Día: ${round(p_meta):,}\n"
                msg += f"  ↳ Faltante Meta: ${round(p_faltante):,}\n\n"
                
            msg += f"──────────────────\n"
            msg += f"📲 Para ver el detalle por oficina, responde con el número del promotor (Ej: *1*)\n"
            msg += f"💪 ¡Vamos por la meta! 🚀"

        return {
            "text": msg,
            "report_type": "prompt_promoter",
            "is_coordinator": True,
            "promoter_list": promoter_compliance_list
        }

    # Early return for coordinator looking at a specific promoter's offices
    if is_coordinator and report_type == "coordinator_promoter_detail":
        if selected_product and selected_product.isdigit():
            idx = int(selected_product) - 1
            if 0 <= idx < len(promoter_compliance_list):
                selected_promoter_name = promoter_compliance_list[idx][0]
                # Recursively call the function as if the coordinator is that promoter requesting "offices"
                result = get_whatsapp_query(
                    phone=None,
                    report_type="offices",
                    selected_product=None,
                    override_promoter_name=selected_promoter_name,
                    override_coordinator_name=None,
                    ref_date=ref_date,
                )
                result["is_coordinator"] = True
                result["report_type"] = "coordinator_promoter_offices_view"
                return result
            else:
                return {
                    "text": "❌ El número ingresado no corresponde a ningún promotor de la lista.",
                    "report_type": "coordinator_promoter_detail",
                    "is_coordinator": True
                }
        else:
            return {
                "text": "❌ Formato inválido. Por favor, responde únicamente con el número del promotor.",
                "report_type": "coordinator_promoter_detail",
                "is_coordinator": True
            }

    # Early return for product list prompt
    if report_type == "prompt_product":
        active_products = sorted([p for p, recs in goals_store.items() if recs and recs[0].get("activo", True)])
        if not active_products:
            return {
                "text": "⚠️ No hay productos con metas activas en este momento."
            }
        msg = f"🔢 *Seleccione un producto para ver el detalle de oficinas:*\n\n"
        for idx, prod in enumerate(active_products, 1):
            msg += f"*{idx}.* {prod}\n"
        msg += f"\nPor favor, escribe el *número* del producto que deseas consultar."
        return {
            "text": msg,
            "report_type": "prompt_product",
            "promoter": user_name
        }
        
    # 3. Obtener catálogo de sitios para mapear sitio -> oficina
    sites_data, _ = get_cached_sales("catalog_sitios")
    site_to_office = {}
    office_names = {} # {cod_oficina: name}
    
    if sites_data:
        for s in sites_data:
            s_code = s.get("Cod_Sitio")
            off_code = s.get("Cod_Oficina")
            off_name = s.get("Oficina", f"Oficina {off_code}")
            if s_code is not None and off_code is not None:
                site_to_office[int(s_code)] = int(off_code)
                office_names[int(off_code)] = off_name
    # Register OWO / APP sites manually to offices 333 / 334
    site_to_office[333033] = 333
    site_to_office[334034] = 334
    office_names[333] = "Ventas OWO"
    office_names[334] = "Ventas APP Su Red"

    # Load products catalog to map cod_producto to product info (same as frontend app.js)
    products_data, _ = get_cached_sales("catalog_productos")
    products_by_code = {}
    if products_data:
        for p in products_data:
            cod = p.get("Cod_Producto")
            if cod is not None:
                products_by_code[str(cod)] = p
                
    # 4. Obtener ventas del día de referencia (hoy o ayer)
    today_str = report_date
    desde = f"{today_str} 00:00:00"
    hasta = f"{today_str} 23:59:59"
    
    sales_list = []
    db_update_time_str = "Desconocida"
    try:
        sales_resp = get_ventas(desde=desde, hasta=hasta, force_refresh=False)
        sales_list = sales_resp.get("data", [])
        last_updated = sales_resp.get("last_updated")
        if last_updated:
            try:
                from datetime import datetime as dt_class
                dt = dt_class.fromisoformat(last_updated)
                db_update_time_str = dt.strftime("%d/%m/%Y %I:%M %p")
            except Exception:
                db_update_time_str = str(last_updated)
                
        if is_past_day:
            db_update_time_str = "Cierre del día"
    except Exception as e:
        logger.error(f"Error fetching sales for WhatsApp query: {e}")
        return {
            "text": f"⚠️ Hola {promoter_name}. No se pudieron consultar las ventas en este momento. Inténtalo de nuevo más tarde."
        }

    # Colombia local time is UTC-5
    from datetime import timezone, timedelta
    colombia_tz = timezone(timedelta(hours=-5))
    now_colombia = datetime.now(colombia_tz)
    ref_hour = now_colombia.hour
    ref_hour = max(7, min(21, ref_hour))
    # Si el reporte es de un día pasado (ej. ayer), el día está cerrado: usar hora tope.
    if is_past_day:
        ref_hour = 21
    ref_hour_str = f"{ref_hour:02d}:00"
    next_hour = ref_hour + 1 if ref_hour < 21 else 21
    next_hour_str = f"{next_hour:02d}:00"
    
    # Calculate weights (same as frontend app.js)
    target_weights = [0.0] * 24
    total_weight = 0.0
    for h in range(7, 22):
        w = 1.0
        if h in (12, 13, 18, 19):
            w = 1.6
        elif h in (7, 21):
            w = 0.5
        target_weights[h] = w
        total_weight += w

    next_hour_ratio = (target_weights[next_hour] / total_weight) if total_weight > 0 else 0.0

    # 5. Agregar ventas por producto, por oficina, y acumuladas
    sales_by_product = {} # {prod_name: total_venta}
    sales_acum_by_product = {} # {prod_name: venta_acum_hasta_ref_hour}
    sales_by_office = {} # {cod_oficina: total_venta}
    total_sales = 0.0
    total_sales_acum = 0.0
    
    for sale in sales_list:
        # Exclude non-sales and payout flows (same as frontend app.js)
        src_table = sale.get("Tabla_Origen")
        s_code = sale.get("Cod_Producto")
        
        # Filter out payouts and general non-sales flows, but preserve CNB (22005)
        if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
            continue

        s_code = sale.get("Cod_Sitio")
        if s_code is not None:
            try:
                s_code_int = int(s_code)
                off_code = site_to_office.get(s_code_int)
                if is_administrator or off_code in assigned_offices:
                    v_neta = float(sale.get("Venta_Neta") or 0.0)
                    prod_name = resolve_product_name(sale, products_by_code)
                    
                    # Filtro para reporte producto/oficina
                    if report_type == "product_office" and prod_name != selected_product:
                        continue
                        
                    increment = v_neta
                    
                    hour_str = sale.get("Hora")
                    sale_hour = 0
                    if hour_str:
                        try:
                            sale_hour = int(hour_str.split(":")[0])
                        except:
                            pass
                            
                    total_sales += increment
                    sales_by_office[off_code] = sales_by_office.get(off_code, 0.0) + increment
                    sales_by_product[prod_name] = sales_by_product.get(prod_name, 0.0) + increment
                    
                    if sale_hour <= ref_hour:
                        total_sales_acum += increment
                        sales_acum_by_product[prod_name] = sales_acum_by_product.get(prod_name, 0.0) + increment
            except:
                pass
                
    # 6. Agregar metas por oficina y por producto para hoy
    goals_by_office = {} # {cod_oficina: total_meta}
    goals_by_product = {} # {prod_name: total_meta}
    total_goals = 0.0
    
    for prod_name, records in goals_store.items():
        if records and not records[0].get("activo", True):
            continue
        # Filtro para reporte producto/oficina
        if report_type == "product_office" and prod_name != selected_product:
            continue
            
        for rec in records:
            if rec.get("fecha") == today_str:
                off_code = rec.get("cod_oficina")
                if off_code is not None:
                    try:
                        off_code_int = int(off_code)
                        if is_administrator or off_code_int in assigned_offices:
                            meta_val = float(rec.get("meta") or 0.0)
                            if prod_name in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}:
                                meta_val = float(round(meta_val))
                            total_goals += meta_val
                            goals_by_office[off_code_int] = goals_by_office.get(off_code_int, 0.0) + meta_val
                            goals_by_product[prod_name] = goals_by_product.get(prod_name, 0.0) + meta_val
                    except:
                        pass

    # 7. Calcular porcentaje de cumplimiento consolidado
    if total_goals > 0:
        compliance = (total_sales / total_goals * 100.0)
    else:
        compliance = 100.0 if total_sales > 0 else 0.0
    emoji_overall = "🟢" if compliance >= 95 else "🔴"

    def compute_monthly_by_product():
        """Devuelve, por producto y para las oficinas asignadas:
        - venta_mes: ventas del día 1 del mes hasta hoy
        - meta_parcial: meta del día 1 hasta hoy (proporcional)
        - meta_full: meta de todo el mes (1 al último día)
        """
        count_based = {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
        current_month = report_date[:7]
        month_start = f"{current_month}-01 00:00:00"
        venta_mes = {}
        try:
            sales_mes_resp = get_ventas(desde=month_start, hasta=hasta, force_refresh=False)
            for sale in sales_mes_resp.get("data", []):
                if sale.get("Tabla_Origen") in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
                    continue
                s_code_m = sale.get("Cod_Sitio")
                if s_code_m is None:
                    continue
                try:
                    off_code_m = site_to_office.get(int(s_code_m))
                except:
                    continue
                if off_code_m in assigned_offices:
                    pname = resolve_product_name(sale, products_by_code)
                    venta_mes[pname] = venta_mes.get(pname, 0.0) + float(sale.get("Venta_Neta") or 0.0)
        except Exception as e:
            logger.error(f"Error fetching monthly sales for WhatsApp report: {e}")

        meta_parcial = {}
        meta_full = {}
        for prod_name_m, records_m in goals_store.items():
            if records_m and not records_m[0].get("activo", True):
                continue
            for rec_m in records_m:
                fecha_m = rec_m.get("fecha")
                if fecha_m and str(fecha_m).startswith(current_month):
                    off_code_g = rec_m.get("cod_oficina")
                    if off_code_g is not None:
                        try:
                            if int(off_code_g) in assigned_offices:
                                val = float(rec_m.get("meta") or 0.0)
                                if prod_name_m in count_based:
                                    val = float(round(val))
                                meta_full[prod_name_m] = meta_full.get(prod_name_m, 0.0) + val
                                if str(fecha_m) <= today_str:
                                    meta_parcial[prod_name_m] = meta_parcial.get(prod_name_m, 0.0) + val
                        except:
                            pass
        return venta_mes, meta_parcial, meta_full

    def month_fragment(p_name, is_count_based, venta_mes, meta_parcial, meta_full):
        """Devuelve (fragmento_porcentajes, lineas_mes) en formato compacto.
        - Parcial: venta del mes / meta del mes a hoy
        - Mensual: venta del mes / meta del mes total
        """
        v = venta_mes.get(p_name, 0.0)
        mp = meta_parcial.get(p_name, 0.0)
        mf = meta_full.get(p_name, 0.0)
        parcial = (v / mp * 100.0) if mp > 0 else (100.0 if v > 0 else 0.0)
        mensual = (v / mf * 100.0) if mf > 0 else (100.0 if v > 0 else 0.0)
        e = lambda p: "🟢" if p >= 95 else "🔴"
        pref = "" if is_count_based else "$"
        pct = f" · 📆 Parcial {e(parcial)}{parcial:.1f}% · Mensual {e(mensual)}{mensual:.1f}%"
        lines = f"  ↳ Mes → Venta {pref}{round(v):,}\n"
        lines += f"  ↳ Mes → Meta a hoy {pref}{round(mp):,} · total {pref}{round(mf):,}\n\n"
        return pct, lines

    def parcial_line(p_name, venta_mes, meta_parcial):
        """Línea de % parcial (venta del mes / meta del mes a hoy) para el reporte de hoy."""
        v = venta_mes.get(p_name, 0.0)
        mp = meta_parcial.get(p_name, 0.0)
        p = (v / mp * 100.0) if mp > 0 else (100.0 if v > 0 else 0.0)
        e = "🟢" if p >= 95 else "🔴"
        return f"  ↳ Parcial (mes a hoy): {e} {p:.1f}%\n\n"

    if is_administrator and report_type in {"products", "offices"}:
        total_faltante_meta = max(0.0, total_goals - total_sales)
        venta_mes_p, meta_parcial_p, meta_full_p = compute_monthly_by_product()
        msg = f"📊 *REPORTE ADMINISTRADOR (GENERAL)*\n"
        msg += f"👤 *Administrador:* {user_name}\n"
        msg += f"📅 *Fecha:* {today_str}\n"
        msg += f"📍 *Ámbito:* Nacional\n"
        msg += f"🔄 *Actualizado DB:* {db_update_time_str}\n"
        msg += f"──────────────────\n"
        msg += f"📦 *Detalle por Producto:*\n\n"

        all_products = sorted(list(set(list(sales_by_product.keys()) + list(goals_by_product.keys()))))
        for p_name in all_products:
            p_sales = sales_by_product.get(p_name, 0.0)
            p_goal = goals_by_product.get(p_name, 0.0)

            if p_goal > 0:
                p_compliance = (p_sales / p_goal * 100.0)
            else:
                p_compliance = 100.0 if p_sales > 0 else 0.0

            e_dia = "🟢" if p_compliance >= 95 else "🔴"
            p_faltante = max(0.0, p_goal - p_sales)

            is_count_based = p_name in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
            pref = "" if is_count_based else "$"
            if is_past_day:
                # Recopilatorio de ayer: compacto con mensual, sin Hora sig.
                pct, mes_lines = month_fragment(p_name, is_count_based, venta_mes_p, meta_parcial_p, meta_full_p)
                msg += f"• 📦 *{p_name}*\n"
                msg += f"  🗓️ Día {e_dia}{p_compliance:.1f}%{pct}\n"
                msg += f"  ↳ Día → Venta {pref}{round(p_sales):,} · Meta {pref}{round(p_goal):,} · Falta {pref}{round(p_faltante):,}\n"
                msg += mes_lines
            else:
                # Hoy: formato original + % parcial del mes.
                msg += f"• 📦 *{p_name}* ({e_dia} *{p_compliance:.1f}%*)\n"
                msg += f"  ↳ Venta Acumulada: {pref}{round(p_sales):,}\n"
                msg += f"  ↳ Meta del Día: {pref}{round(p_goal):,}\n"
                msg += f"  ↳ Faltante Meta: {pref}{round(p_faltante):,}\n"
                msg += parcial_line(p_name, venta_mes_p, meta_parcial_p)

        msg += f"──────────────────\n"
        msg += f"💪 ¡Vamos por la meta! 🚀"

        return {
            "text": msg,
            "report_type": "administrator_general",
            "is_administrator": True,
            "sales": total_sales,
            "goal": total_goals,
            "compliance": compliance
        }

    if is_coordinator and report_type in {"products", "offices"}:
        total_faltante_meta = max(0.0, total_goals - total_sales)
        if is_past_day:
            msg = f"📊 *REPORTE DE ZONA (AYER)*\n"
        else:
            msg = f"📊 *REPORTE DE ZONA (GENERAL)*\n"
        msg += f"👤 *Coordinador:* {user_name}\n"
        msg += f"📅 *Fecha:* {today_str}\n"
        msg += f"📍 *Zona:* {user_zone}\n"
        msg += f"🔄 *Actualizado DB:* {db_update_time_str}\n"
        msg += f"──────────────────\n"
        msg += f"📦 *Detalle por Producto:*\n\n"

        venta_mes_p, meta_parcial_p, meta_full_p = compute_monthly_by_product()
        all_products = sorted(list(set(list(sales_by_product.keys()) + list(goals_by_product.keys()))))
        for p_name in all_products:
            p_sales = sales_by_product.get(p_name, 0.0)
            p_goal = goals_by_product.get(p_name, 0.0)

            if p_goal > 0:
                p_compliance = (p_sales / p_goal * 100.0)
            else:
                p_compliance = 100.0 if p_sales > 0 else 0.0

            e_dia = "🟢" if p_compliance >= 95 else "🔴"
            p_next_hour_goal = p_goal * next_hour_ratio
            p_faltante = max(0.0, p_goal - p_sales)

            is_count_based = p_name in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
            pref = "" if is_count_based else "$"
            if is_past_day:
                # Recopilatorio de ayer: compacto con mensual, sin Hora sig.
                pct, mes_lines = month_fragment(p_name, is_count_based, venta_mes_p, meta_parcial_p, meta_full_p)
                msg += f"• 📦 *{p_name}*\n"
                msg += f"  🗓️ Día {e_dia}{p_compliance:.1f}%{pct}\n"
                msg += f"  ↳ Día → Meta {pref}{round(p_goal):,} · Falta {pref}{round(p_faltante):,}\n"
                msg += mes_lines
            else:
                # Hoy: formato original + % parcial del mes.
                msg += f"• 📦 *{p_name}* ({e_dia} *{p_compliance:.1f}%*)\n"
                msg += f"  ↳ Meta del Día: {pref}{round(p_goal):,}\n"
                msg += f"  ↳ Meta Hora Sig: {pref}{round(p_next_hour_goal):,}\n"
                msg += f"  ↳ Faltante Meta: {pref}{round(p_faltante):,}\n"
                msg += parcial_line(p_name, venta_mes_p, meta_parcial_p)

        msg += f"──────────────────\n"
        msg += f"💪 ¡Vamos por la meta! 🚀"

        return {
            "text": msg,
            "report_type": "coordinator_general",
            "is_coordinator": True,
            "promoter": user_name,
            "sales": total_sales,
            "goal": total_goals,
            "compliance": compliance
        }
    
    if report_type == "products":
        total_faltante_meta = max(0.0, total_goals - total_sales)
        if is_past_day:
            msg = f"📊 *TU RESUMEN DE AYER*\n"
        else:
            msg = f"📊 *CUMPLIMIENTO DIARIO POR PRODUCTO*\n"
        msg += f"👤 *{user_label}:* {user_name}\n"
        msg += f"📅 *Fecha:* {today_str}\n"
        msg += f"📍 *Zona:* {user_zone}\n"
        msg += f"🔄 *Actualizado DB:* {db_update_time_str}\n"
        msg += f"──────────────────\n"
        msg += f"📦 *Detalle por Producto:*\n"

        venta_mes_p, meta_parcial_p, meta_full_p = compute_monthly_by_product()
        all_products = sorted(list(set(list(sales_by_product.keys()) + list(goals_by_product.keys()))))
        for p_name in all_products:
            p_goal = goals_by_product.get(p_name, 0.0)
            p_sales_total = sales_by_product.get(p_name, 0.0)

            if p_goal > 0:
                p_compliance = (p_sales_total / p_goal * 100.0)
            else:
                p_compliance = 100.0 if p_sales_total > 0 else 0.0

            e_dia = "🟢" if p_compliance >= 95 else "🔴"
            p_next_hour_goal = p_goal * next_hour_ratio
            p_faltante = max(0.0, p_goal - p_sales_total)

            is_count_based = p_name in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
            pref = "" if is_count_based else "$"
            if is_past_day:
                # Recopilatorio de ayer: compacto con mensual, sin Hora sig.
                pct, mes_lines = month_fragment(p_name, is_count_based, venta_mes_p, meta_parcial_p, meta_full_p)
                msg += f"• 📦 *{p_name}*\n"
                msg += f"  🗓️ Día {e_dia}{p_compliance:.1f}%{pct}\n"
                msg += f"  ↳ Día → Meta {pref}{round(p_goal):,} · Falta {pref}{round(p_faltante):,}\n"
                msg += mes_lines
            else:
                # Hoy: formato original + % parcial del mes.
                msg += f"• 📦 *{p_name}* ({e_dia} *{p_compliance:.1f}%*)\n"
                msg += f"  ↳ Meta del Día: {pref}{round(p_goal):,}\n"
                msg += f"  ↳ Meta Hora Sig: {pref}{round(p_next_hour_goal):,}\n"
                msg += f"  ↳ Faltante Meta: {pref}{round(p_faltante):,}\n"
                msg += parcial_line(p_name, venta_mes_p, meta_parcial_p)
        msg += f"──────────────────\n"
        msg += f"💪 ¡Vamos por la meta! 🚀"

    elif report_type == "product_office":
        is_count_based = selected_product in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
        total_faltante_meta = max(0.0, total_goals - total_sales)
        
        if is_past_day:
            msg = f"📊 *REPORTE PRODUCTO / OFICINA (AYER)*\n"
        else:
            msg = f"📊 *REPORTE PRODUCTO / OFICINA*\n"
        msg += f"👤 *{user_label}:* {user_name}\n"
        msg += f"📅 *Fecha:* {today_str}\n"
        msg += f"📦 *Producto:* *{selected_product}*\n"
        msg += f"🔄 *Actualizado DB:* {db_update_time_str}\n"
        msg += f"──────────────────\n"
        if is_count_based:
            msg += f"📊 *Cumplimiento:* {emoji_overall} *{compliance:.1f}%*\n"
            msg += f"📈 *Meta del Día:* {round(total_goals):,}\n"
            msg += f"🎯 *Faltante Meta:* {round(total_faltante_meta):,}\n"
        else:
            msg += f"📊 *Cumplimiento:* {emoji_overall} *{compliance:.1f}%*\n"
            msg += f"📈 *Meta del Día:* ${round(total_goals):,}\n"
            msg += f"🎯 *Faltante Meta:* ${round(total_faltante_meta):,}\n"
        msg += f"──────────────────\n"
        msg += f"🏢 *Detalle por Oficina:*\n"
        
        sorted_office_codes = sorted(list(assigned_offices))
        for off_code in sorted_office_codes:
            off_name = office_names.get(off_code, f"Oficina {off_code}")
            off_sales = sales_by_office.get(off_code, 0.0)
            off_goal = goals_by_office.get(off_code, 0.0)
            
            if off_goal > 0:
                off_comp = (off_sales / off_goal * 100.0)
            else:
                off_comp = 100.0 if off_sales > 0 else 0.0
                
            emoji_off = "🟢" if off_comp >= 95 else "🔴"
            off_faltante = max(0.0, off_goal - off_sales)
            
            if is_count_based:
                msg += f"• 🏢 *{off_name}* ({emoji_off} *{off_comp:.1f}%*)\n"
                msg += f"  ↳ Meta del Día: {round(off_goal):,}\n"
                msg += f"  ↳ Faltante Meta: {round(off_faltante):,}\n\n"
            else:
                msg += f"• 🏢 *{off_name}* ({emoji_off} *{off_comp:.1f}%*)\n"
                msg += f"  ↳ Meta del Día: ${round(off_goal):,}\n"
                msg += f"  ↳ Faltante Meta: ${round(off_faltante):,}\n\n"
                
        msg += f"──────────────────\n"
        msg += f"💪 ¡Vamos por la meta! 🚀"
        
    else: # report_type == "offices"
        if is_past_day:
            msg = f"📊 *REPORTE OFICINA GENERAL (AYER)*\n"
        else:
            msg = f"📊 *REPORTE OFICINA GENERAL*\n"
        msg += f"👤 *{user_label}:* {user_name}\n"
        msg += f"📅 *Fecha:* {today_str}\n"
        msg += f"📍 *Zona:* {user_zone}\n"
        msg += f"──────────────────\n"
        msg += f"💰 *Ventas:* ${round(total_sales):,}\n"
        msg += f"🎯 *Meta:* ${round(total_goals):,}\n"
        msg += f"📈 *Cumplimiento:* {emoji_overall} *{compliance:.1f}%*\n"
        msg += f"──────────────────\n"
        msg += f"🏢 *Detalle por Oficina:*\n"
        
        sorted_office_codes = sorted(list(assigned_offices))
        for off_code in sorted_office_codes:
            off_name = office_names.get(off_code, f"Oficina {off_code}")
            off_sales = sales_by_office.get(off_code, 0.0)
            off_goal = goals_by_office.get(off_code, 0.0)
            
            if off_goal > 0:
                off_comp = (off_sales / off_goal * 100.0)
            else:
                off_comp = 100.0 if off_sales > 0 else 0.0
                
            emoji_off = "🟢" if off_comp >= 95 else "🔴"
            msg += f"• 🏢 *{off_name}* ({emoji_off} *{off_comp:.1f}%*)\n"
            msg += f"  ↳ Venta: ${round(off_sales):,} / Meta: ${round(off_goal):,}\n"
            
        msg += f"──────────────────\n"
        msg += f"💪 ¡Vamos por la meta! 🚀"
        
    ret = {
        "text": msg,
        "report_type": report_type,
        "promoter": user_name,
        "sales": total_sales,
        "goal": total_goals,
        "compliance": compliance
    }
    if override_promoter_name:
        ret["is_coordinator_promoter_view"] = True
    return ret

@app.get("/api/sitios")
def get_sitios(
    force_refresh: bool = Query(False, description="Forzar consulta a Oracle y refrescar catálogo de sitios"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Returns the list of sales offices and sites.
    Caches the results in SQLite to allow instant loading of filters.
    """
    cache_key = "catalog_sitios"
    cached_data, last_updated = get_cached_sales(cache_key)
    
    if cached_data is not None and not force_refresh:
        logger.info("Serving sites catalogue from SQLite Cache.")
        return {"source": "LOCAL_CACHE", "last_updated": last_updated, "data": cached_data}
        
    logger.info("Fetching sites catalogue from Oracle...")
    results = []
    
    # Try CAUCAMED first, then FORTUMED
    for pool, label in [(db_manager.pool_cauca, "CAUCAMED"), (db_manager.pool_fortuna, "FORTUMED")]:
        if pool:
            try:
                with pool.acquire() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(SITIOS_VENTA_QUERY)
                        res = rows_to_dicts(cursor)
                        logger.info(f"Loaded {len(res)} sites from {label}")
                        # Cache the results
                        set_cached_sales(cache_key, res)
                        return {"source": label, "data": res}
            except Exception as e:
                logger.error(f"Failed to fetch sites from {label}: {e}")
                
    # Fallback to stale cache if DB query failed
    if cached_data is not None:
        logger.warning("Failed to query sites from database, serving stale cache.")
        return {"source": "LOCAL_CACHE_STALE", "last_updated": last_updated, "data": cached_data}
        
    # Fallback: Compile from metas or load empty
    sites = {}
    for prod, goals in goals_store.items():
        for g in goals:
            sid = g["cod_sitio"]
            if sid not in sites:
                sites[sid] = {
                    "Cod_Sitio": sid,
                    "Sitio_Venta": g["sitio_venta"],
                    "Cod_Oficina": g["cod_oficina"],
                    "Oficina": f"Oficina {g['cod_oficina']}",
                    "Zona": "Norte" # Default or placeholder
                }
                
    if sites:
        logger.info(f"Compiled {len(sites)} sites from local loaded metas.")
        return {"source": "METAS_EXCEL_FALLBACK", "data": list(sites.values())}
        
    # Minimum defaults
    return {
        "source": "DEFAULTS",
        "data": [
            {"Cod_Sitio": 5006, "Sitio_Venta": "Antes De Llegar Al Puente", "Cod_Oficina": 5, "Oficina": "El Terminal - Timba", "Zona": "Norte"},
            {"Cod_Sitio": 5001, "Sitio_Venta": "Of El Terminal - Timba", "Cod_Oficina": 5, "Oficina": "El Terminal - Timba", "Zona": "Norte"},
            {"Cod_Sitio": 507901, "Sitio_Venta": "Movil Portales", "Cod_Oficina": 507, "Oficina": "Esquina Parque Villa Rica", "Zona": "Norte"},
            {"Cod_Sitio": 9026, "Sitio_Venta": "TAT Duvan El Pital", "Cod_Oficina": 9, "Oficina": "Estacion De Policia", "Zona": "Norte"},
            {"Cod_Sitio": 4037, "Sitio_Venta": "TAT Duvan Monterilla Santander", "Cod_Oficina": 4, "Oficina": "Mondomo", "Zona": "Norte"}
        ]
    }

@app.get("/api/productos")
def get_productos(
    force_refresh: bool = Query(False, description="Forzar consulta a Oracle y refrescar catálogo de productos"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Returns catalogue of products.
    Caches the results in SQLite to allow instant loading of filters.
    """
    cache_key = "catalog_productos"
    cached_data, last_updated = get_cached_sales(cache_key)
    
    if cached_data is not None and not force_refresh:
        logger.info("Serving products catalogue from SQLite Cache.")
        return {"source": "LOCAL_CACHE", "last_updated": last_updated, "data": cached_data}
        
    logger.info("Fetching products catalogue from Oracle...")
    if db_manager.pool_cauca:
        try:
            with db_manager.get_cauca_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(PRODUCTOS_QUERY)
                    res = rows_to_dicts(cursor)
                    # Cache the results
                    set_cached_sales(cache_key, res)
                    return {"source": "DATABASE", "data": res}
        except Exception as e:
            logger.error(f"Failed to fetch products from DB: {e}")
            
    # Fallback to stale cache if DB query failed
    if cached_data is not None:
        logger.warning("Failed to query products from database, serving stale cache.")
        return {"source": "LOCAL_CACHE_STALE", "last_updated": last_updated, "data": cached_data}
        
    # Default list of popular products
    return {
        "source": "DEFAULTS",
        "data": [
            {"Cod_Producto": 5, "Producto": "SUPER ASTRO", "Tipo_Producto": "ASTRO"},
            {"Cod_Producto": 22005, "Producto": "TRANSACCIONES CNB", "Tipo_Producto": "CNB"},
            {"Cod_Producto": 22069, "Producto": "CHANCE RASPA", "Tipo_Producto": "RASPA"},
            {"Cod_Producto": 13, "Producto": "GIROS CREADOS", "Tipo_Producto": "GIROS"}
        ]
    }


# ============================ BETPLAY ============================

# Configuration per Betplay transaction type: which query to run and which
# columns hold the amount and the event date.
BETPLAY_CONFIG = {
    "pagos": {
        "query": PAGOS_BETPLAY_COMPLETO,
        "amount_key": "VALOR_PAGO",
        "date_key": "FEC_PAGO",
        # Cédula del CLIENTE final (distinta del vendedor NUM_IDENTIFICACION).
        "client_key": "IDENTIFICACION",
    },
    "recargas": {
        "query": RECARGAS_BETPLAY_COMPLETO,
        "amount_key": "VLR_RECARGA",
        "date_key": "FEC_VENTA",
        # En recargas el identificador del cliente es el número de celular.
        "client_key": "NUM_CELULAR",
    },
}


def _to_float(val):
    """Safe numeric conversion; returns 0.0 for None/invalid values."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _hour_of(date_str):
    """Extracts the hour (0-23) from an ISO datetime string; None if unparseable."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(str(date_str)).hour
    except ValueError:
        return None


def _day_of(date_str):
    """Extracts the day 'YYYY-MM-DD' from an ISO datetime string; None if unparseable."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(str(date_str)).date().isoformat()
    except ValueError:
        return None


def aggregate_betplay(rows, amount_key, date_key, client_key=None):
    """
    Builds pre-calculated aggregations over raw Betplay rows.
    Each group carries both 'monto' (sum of amount) and 'cantidad' (row count).

    client_key: columna con la cédula/identificador del CLIENTE final
    (IDENTIFICACION en pagos, NUM_CELULAR en recargas). Se usa para contar
    clientes únicos (globales y por sitio), aparte de los usuarios/vendedores.
    """
    by_hour = {}        # hour(int) -> {monto, cantidad}
    by_day = {}         # 'YYYY-MM-DD' -> {monto, cantidad}
    by_zone = {}        # zona -> {monto, cantidad}
    by_city = {}        # ciudad -> {monto, cantidad}
    by_type_sv = {}     # tipo SV -> {monto, cantidad}
    by_office = {}      # cod_oficina -> {oficina, monto, cantidad}
    by_site = {}        # cod_sitio -> {sitio, oficina, zona, ciudad, tipo_sv, cx, cy, monto, cantidad}
    by_user = {}        # identificacion -> {monto, cantidad}
    by_channel = {}     # canal -> {monto, cantidad}
    site_clients = {}   # cod_sitio -> set(client ids)  (para contar clientes por sitio)

    total_monto = 0.0
    total_cantidad = 0
    usuarios = set()
    clientes = set()
    sitios = set()

    def bump(d, key, monto, **labels):
        if key not in d:
            d[key] = {"monto": 0.0, "cantidad": 0, **labels}
        d[key]["monto"] += monto
        d[key]["cantidad"] += 1

    for r in rows:
        monto = _to_float(r.get(amount_key))
        total_monto += monto
        total_cantidad += 1

        # Por hora / por día
        h = _hour_of(r.get(date_key))
        if h is not None:
            bump(by_hour, h, monto)
        d = _day_of(r.get(date_key))
        if d is not None:
            bump(by_day, d, monto)

        # Por zona
        zona = r.get("Zona") or "Sin Zona"
        bump(by_zone, zona, monto)

        # Por ciudad
        ciudad = r.get("Ciudad") or "Sin Ciudad"
        bump(by_city, ciudad, monto, ciudad=ciudad)

        # Por tipo de sitio de venta
        tipo = r.get("Tipo SV") or "Sin Tipo"
        bump(by_type_sv, tipo, monto)

        # Por oficina
        cod_of = r.get("Cod. Oficina")
        bump(by_office, cod_of, monto, oficina=(r.get("Oficina") or "Sin Oficina"), cod_oficina=cod_of)

        # Por sitio (incluye coordenadas para el mapa, municipio y tipo SV)
        cod_sitio = r.get("Cod. Sitio")
        bump(
            by_site, cod_sitio, monto,
            cod_sitio=cod_sitio,
            sitio=(r.get("Sitio de venta") or "Sin Sitio"),
            oficina=(r.get("Oficina") or "Sin Oficina"),
            zona=zona,
            ciudad=ciudad,
            tipo_sv=tipo,
            cx=r.get("CX"),
            cy=r.get("CY"),
        )
        if cod_sitio is not None:
            sitios.add(cod_sitio)

        # Por usuario/vendedor (número de identificación del usuario del sistema)
        ident = r.get("NUM_IDENTIFICACION")
        if ident is not None and str(ident).strip() != "":
            bump(by_user, ident, monto, identificacion=ident)
            usuarios.add(ident)

        # Por CLIENTE final (IDENTIFICACION en pagos / NUM_CELULAR en recargas)
        if client_key:
            cli = r.get(client_key)
            if cli is not None and str(cli).strip() != "":
                clientes.add(cli)
                if cod_sitio is not None:
                    site_clients.setdefault(cod_sitio, set()).add(cli)

        # Por canal
        canal = r.get("IDE_CANAL")
        bump(by_channel, canal if canal is not None else "Sin Canal", monto, canal=canal)

    # Sort helpers
    def as_sorted_list(d, sort_key="monto", reverse=True, label_key=None):
        items = []
        for k, v in d.items():
            entry = dict(v)
            if label_key:
                entry[label_key] = k
            items.append(entry)
        items.sort(key=lambda x: x.get(sort_key, 0), reverse=reverse)
        return items

    # Enriquecer cada sitio con clientes únicos y ticket promedio por transacción.
    for cod_sitio, entry in by_site.items():
        entry["clientes"] = len(site_clients.get(cod_sitio, ()))
        cant = entry.get("cantidad", 0)
        entry["ticket_promedio"] = round(entry.get("monto", 0) / cant, 2) if cant else 0

    return {
        "totales": {
            "monto": round(total_monto, 2),
            "cantidad": total_cantidad,
            "usuarios_unicos": len(usuarios),
            "clientes_unicos": len(clientes),
            "sitios_unicos": len(sitios),
            "ticket_promedio": round(total_monto / total_cantidad, 2) if total_cantidad else 0,
        },
        # por_hora / por_dia ordenados cronológicamente
        "por_hora": [
            {"hora": h, **by_hour[h]} for h in sorted(by_hour.keys())
        ],
        "por_dia": [
            {"fecha": d, **by_day[d]} for d in sorted(by_day.keys())
        ],
        "por_zona": as_sorted_list(by_zone, label_key="zona"),
        "por_ciudad": as_sorted_list(by_city),
        "por_tipo_sv": as_sorted_list(by_type_sv, label_key="tipo"),
        "por_oficina": as_sorted_list(by_office),
        "por_sitio": as_sorted_list(by_site),
        "por_usuario": as_sorted_list(by_user),
        "por_canal": as_sorted_list(by_channel, label_key="canal_label"),
    }


def _fetch_betplay_rows(query, desde, hasta):
    """Ejecuta una query Betplay en ambas BD y devuelve (rows, errors, db_failures)."""
    rows, errors, db_failures = [], [], False
    params = {"desde": desde, "hasta": hasta}
    for db_name, get_conn, pool in (
        ("CAUCAMED", db_manager.get_cauca_connection, db_manager.pool_cauca),
        ("FORTUMED", db_manager.get_fortuna_connection, db_manager.pool_fortuna),
    ):
        if not pool:
            errors.append(f"{db_name} pool not initialized.")
            db_failures = True
            continue
        try:
            with get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    res = rows_to_dicts(cursor)
                    for r in res:
                        r["Fuente"] = "CAUCA" if db_name == "CAUCAMED" else "FORTUNA"
                    rows.extend(res)
                    logger.info(f"Retrieved {len(res)} Betplay rows from {db_name}.")
        except Exception as e:
            msg = f"{db_name} Betplay query failed: {e}"
            logger.error(msg)
            errors.append(msg)
            db_failures = True
    return rows, errors, db_failures


# Claves unificadas usadas cuando tipo == 'ambos' (pagos + recargas juntos).
BETPLAY_UNIFIED = {"amount_key": "VALOR_UNIFICADO", "date_key": "FECHA_UNIFICADA", "client_key": "CLIENTE_UNIFICADO"}


def compute_betplay_resumen(tipo, desde, hasta, force_refresh=False):
    """
    Núcleo reutilizable: devuelve (resultado_dict) con las agregaciones de Betplay
    para el periodo. Usado por el endpoint /resumen y por el asistente IA.
    tipo: 'pagos' | 'recargas' | 'ambos' (combina ambos).
    """
    tipo = (tipo or "").lower().strip()
    if tipo not in BETPLAY_CONFIG and tipo != "ambos":
        raise HTTPException(status_code=400, detail="tipo debe ser 'pagos', 'recargas' o 'ambos'.")

    cache_key = f"betplay_{tipo}_{desde}_{hasta}"

    # 1. Serve from cache unless forcing refresh
    cached_data, last_updated = get_cached_sales(cache_key)
    if cached_data is not None and not force_refresh:
        logger.info(f"Serving Betplay '{tipo}' summary from SQLite Cache (key {cache_key}).")
        return {"source": "LOCAL_CACHE", "last_updated": last_updated, "tipo": tipo, "data": cached_data}

    logger.info(f"Fetching Betplay '{tipo}' from Oracle: {desde} -> {hasta}")

    # 2. Fetch rows (una o ambas queries según el tipo)
    errors = []
    db_failures = False
    if tipo == "ambos":
        rows = []
        for sub in ("pagos", "recargas"):
            cfg = BETPLAY_CONFIG[sub]
            sub_rows, sub_err, sub_fail = _fetch_betplay_rows(cfg["query"], desde, hasta)
            errors.extend(sub_err)
            db_failures = db_failures or sub_fail
            # Normalizar a columnas unificadas para agregar todo junto.
            for r in sub_rows:
                r["TIPO_TX"] = "Pago" if sub == "pagos" else "Recarga"
                r["VALOR_UNIFICADO"] = r.get(cfg["amount_key"])
                r["FECHA_UNIFICADA"] = r.get(cfg["date_key"])
                r["CLIENTE_UNIFICADO"] = r.get(cfg["client_key"])
            rows.extend(sub_rows)
        agg_cfg = BETPLAY_UNIFIED
    else:
        cfg = BETPLAY_CONFIG[tipo]
        rows, errors, db_failures = _fetch_betplay_rows(cfg["query"], desde, hasta)
        agg_cfg = cfg

    # 3. Fallback to stale cache if DB failed and we have something cached
    if db_failures and not rows and cached_data is not None:
        logger.warning(f"Betplay DB query failed. Serving stale cache. Errors: {errors}")
        return {"source": "LOCAL_CACHE_STALE", "last_updated": last_updated, "tipo": tipo, "data": cached_data}

    # 4. Aggregate and cache (incluye filas crudas con tope para no inflar el payload).
    # Tope amplio porque el filtrado del dashboard se hace en el navegador sobre
    # estas filas; si se supera, los filtros operan sobre una muestra.
    DETALLE_LIMIT = 20000
    resumen = aggregate_betplay(rows, agg_cfg["amount_key"], agg_cfg["date_key"], client_key=agg_cfg.get("client_key"))
    resumen["detalle"] = rows[:DETALLE_LIMIT]
    resumen["detalle_total"] = len(rows)
    set_cached_sales(cache_key, resumen)

    return {"source": "DATABASE", "tipo": tipo, "desde": desde, "hasta": hasta, "errors": errors, "data": resumen}


@app.get("/api/betplay/resumen")
def get_betplay_resumen(
    tipo: str = Query("pagos", description="Tipo de transacción: 'pagos' o 'recargas'"),
    desde: str = Query(..., description="Fecha inicio YYYY-MM-DD HH:MM:SS"),
    hasta: str = Query(..., description="Fecha fin (exclusiva) YYYY-MM-DD HH:MM:SS"),
    force_refresh: bool = Query(False, description="Forzar consulta a Oracle y refrescar caché"),
):
    """
    Returns pre-calculated aggregations of Betplay payments/recharges for the
    given period, querying both CAUCAMED and FORTUMED. Cached in SQLite per key.
    """
    return compute_betplay_resumen(tipo, desde, hasta, force_refresh)


# ============================ ASISTENTE IA ============================

# Configuración del modelo (LM Studio en Mac local, API compatible con OpenAI).
# Los valores por defecto están "quemados" para que producción funcione aunque
# no exista el archivo .env; pueden sobreescribirse vía variables de entorno.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://10.0.29.27:1234/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma-4-e4b-it-qat")
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")
LLM_MAX_SQL_ITERS = int(os.getenv("LLM_MAX_SQL_ITERS", "3"))
LLM_SQL_ROW_LIMIT = int(os.getenv("LLM_SQL_ROW_LIMIT", "200"))

# Herramienta web del asistente (búsqueda en internet). Presupuesto de
# iteraciones SEPARADO del de SQL: las búsquedas no consumen los turnos de datos.
# WEB_SEARCH_ENABLED gobierna el acceso a internet (toggle del usuario).
WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "1") not in ("0", "false", "False", "")
LLM_MAX_WEB_ITERS = int(os.getenv("LLM_MAX_WEB_ITERS", "3"))
WEB_SEARCH_TIMEOUT = int(os.getenv("WEB_SEARCH_TIMEOUT", "8"))
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))

# Topes del CONTEXTO agregado que se inyecta al modelo en cada mensaje.
# Ajustables por variable de entorno para reducir el tamaño del prompt sin
# tocar el código. Valores por defecto = recorte "moderado".
CTX_CIUDAD_TOP = int(os.getenv("CTX_CIUDAD_TOP", "10"))
CTX_OFICINA_TOP = int(os.getenv("CTX_OFICINA_TOP", "5"))
CTX_SITIOS_TOP = int(os.getenv("CTX_SITIOS_TOP", "5"))
CTX_USUARIOS_TOP = int(os.getenv("CTX_USUARIOS_TOP", "5"))
CTX_HISTORIAL_DIAS = int(os.getenv("CTX_HISTORIAL_DIAS", "14"))

# Host base de LM Studio (sin /v1), para la REST API nativa de control de modelos
# (POST /api/v1/models/load y /unload, GET /api/v0/models).
LLM_HOST = LLM_BASE_URL.rsplit("/v1", 1)[0].rstrip("/")

# Catálogo de modelos seleccionables por el usuario, con nombres amigables
# (nivel de "inteligencia"). El id DEBE coincidir (minúsculas) con LM Studio.
ASSISTANT_MODELS = [
    {"id": "gemma-4-e2b-it-qat", "label": "Inteligencia Baja"},
    {"id": "gemma-4-e4b-it-qat", "label": "Inteligencia Media"},
    {"id": "gemma-4-12b-it-qat", "label": "Inteligencia Alta"},
]
_ASSISTANT_MODEL_IDS = {m["id"] for m in ASSISTANT_MODELS}

# Modelos con capacidad de visión (aceptan imágenes). Solo el 12B la tiene.
# Las imágenes adjuntas solo se envían al modelo si es uno de estos.
VISION_MODEL_IDS = {"gemma-4-12b-it-qat"}

# Límites de adjuntos (para no desbordar el contexto ni la memoria).
UPLOAD_MAX_BYTES = int(os.getenv("ASSISTANT_UPLOAD_MAX_MB", "10")) * 1024 * 1024
PDF_TEXT_MAX_CHARS = int(os.getenv("ASSISTANT_PDF_TEXT_MAX_CHARS", "12000"))


@app.get("/api/assistant/health")
def assistant_health():
    """
    Verifica si la API del modelo (LM Studio en la Mac) está accesible.
    Hace un GET a {LLM_BASE_URL}/models con timeout corto.
    """
    import urllib.request
    import urllib.error

    url = LLM_BASE_URL.rstrip("/") + "/models"
    try:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer lm-studio"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        # LM Studio devuelve { "data": [ { "id": "..." }, ... ] }
        models = [m.get("id") for m in payload.get("data", [])] if isinstance(payload, dict) else []
        return {"online": True, "base_url": LLM_BASE_URL, "configured_model": LLM_MODEL, "models": models}
    except Exception as e:
        logger.warning(f"Assistant health check failed: {e}")
        return {"online": False, "base_url": LLM_BASE_URL, "configured_model": LLM_MODEL, "error": str(e)}


_llm_client = None


def get_llm_client():
    """Lazy singleton del cliente OpenAI apuntando a LM Studio."""
    global _llm_client
    if _llm_client is None:
        from openai import OpenAI
        _llm_client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    return _llm_client


# ---- Control nativo de modelos en LM Studio (load/unload) ----

def _lmstudio_request(method, path, body=None, timeout=10):
    """Hace una petición HTTP a la REST API nativa de LM Studio."""
    import urllib.request
    url = LLM_HOST + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


def _lmstudio_loaded_llms():
    """Devuelve la lista de ids de modelos LLM actualmente cargados (state=loaded)."""
    payload = _lmstudio_request("GET", "/api/v0/models", timeout=5)
    out = []
    for m in (payload.get("data", []) if isinstance(payload, dict) else []):
        if m.get("type") in ("llm", "vlm") and m.get("state") == "loaded":
            out.append(m.get("id"))
    return out


def _current_catalog_model():
    """
    Devuelve el id del modelo del catálogo que esté actualmente cargado en
    LM Studio, o None si ninguno del catálogo está cargado. Útil para arrancar
    usando lo que ya está cargado sin forzar un swap.
    """
    try:
        for mid in _lmstudio_loaded_llms():
            if mid in _ASSISTANT_MODEL_IDS:
                return mid
    except Exception as e:
        logger.warning(f"No se pudo determinar el modelo cargado: {e}")
    return None


def ensure_model_loaded(target):
    """
    Garantiza que `target` sea el modelo cargado en LM Studio, descargando
    cualquier otro LLM cargado (eject) y cargando el solicitado si hace falta.
    Devuelve dict con el resultado. Best-effort: si LM Studio no soporta algún
    paso, se reporta el error pero no se lanza excepción.
    """
    result = {"model": target, "swapped": False, "unloaded": [], "load_time_seconds": None}
    try:
        loaded = _lmstudio_loaded_llms()
    except Exception as e:
        result["error"] = f"No se pudo consultar modelos cargados: {e}"
        return result

    if target in loaded:
        result["already_loaded"] = True
        return result

    # Eject de los demás LLM cargados.
    for mid in loaded:
        if mid == target:
            continue
        try:
            _lmstudio_request("POST", "/api/v1/models/unload", {"instance_id": mid}, timeout=30)
            result["unloaded"].append(mid)
        except Exception as e:
            logger.warning(f"No se pudo descargar el modelo {mid}: {e}")

    # Carga del modelo solicitado (puede tardar para modelos grandes).
    try:
        loaded_info = _lmstudio_request("POST", "/api/v1/models/load", {"model": target}, timeout=180)
        result["swapped"] = True
        result["load_time_seconds"] = loaded_info.get("load_time_seconds")
    except Exception as e:
        result["error"] = f"No se pudo cargar el modelo {target}: {e}"
    return result


@app.get("/api/assistant/models")
def assistant_models():
    """
    Catálogo de modelos seleccionables (nombres amigables) y su estado de carga
    en LM Studio, más el modelo configurado por defecto.
    """
    try:
        loaded = set(_lmstudio_loaded_llms())
    except Exception as e:
        logger.warning(f"No se pudo consultar estado de modelos: {e}")
        loaded = set()
    models = [
        {"id": m["id"], "label": m["label"], "loaded": m["id"] in loaded,
         "vision": m["id"] in VISION_MODEL_IDS}
        for m in ASSISTANT_MODELS
    ]
    return {"models": models, "default": LLM_MODEL}


class AssistantModelSelectRequest(BaseModel):
    model: str


@app.post("/api/assistant/model/select")
def assistant_model_select(req: AssistantModelSelectRequest):
    """
    Cambia el modelo activo en LM Studio: descarga el actual y carga el pedido.
    """
    if req.model not in _ASSISTANT_MODEL_IDS:
        return {"ok": False, "error": f"Modelo no permitido: {req.model}"}
    res = ensure_model_loaded(req.model)
    res["ok"] = "error" not in res
    return res


def _compact_resumen_for_context(tipo, desde, hasta):
    """
    Construye una versión compacta del resumen agregado (sin filas crudas)
    para inyectar como contexto al modelo. Recorta listas largas a top-N.
    """
    try:
        result = compute_betplay_resumen(tipo, desde, hasta, force_refresh=False)
    except Exception as e:
        logger.error(f"No se pudo calcular resumen para contexto ({tipo}): {e}")
        return {"tipo": tipo, "error": str(e)}

    data = result.get("data", {}) or {}
    return {
        "tipo": tipo,
        "totales": data.get("totales", {}),
        "por_hora": data.get("por_hora", []),
        "por_zona": data.get("por_zona", []),
        "por_ciudad": (data.get("por_ciudad", []) or [])[:CTX_CIUDAD_TOP],
        "por_tipo_sv": data.get("por_tipo_sv", []),
        "por_oficina": (data.get("por_oficina", []) or [])[:CTX_OFICINA_TOP],
        "top_sitios": (data.get("por_sitio", []) or [])[:CTX_SITIOS_TOP],
        "top_usuarios": (data.get("por_usuario", []) or [])[:CTX_USUARIOS_TOP],
        "por_canal": data.get("por_canal", []),
    }


def _betplay_historial_diario(dias=28):
    """
    Devuelve los totales por día de pagos y recargas de los últimos `dias` días
    (para que el asistente pueda hacer proyecciones). Usa caché por rango.
    """
    today = date.today()
    desde = f"{(today - timedelta(days=dias)).isoformat()} 00:00:00"
    hasta = f"{(today + timedelta(days=1)).isoformat()} 00:00:00"
    series = {}
    for tipo in ("pagos", "recargas"):
        try:
            result = compute_betplay_resumen(tipo, desde, hasta, force_refresh=False)
            series[tipo] = (result.get("data", {}) or {}).get("por_dia", [])
        except Exception as e:
            logger.error(f"No se pudo calcular historial diario ({tipo}): {e}")
            series[tipo] = []
    return {"desde": desde, "hasta": hasta, "dias": dias, "por_dia": series}


# ==================================================================
#  ASISTENTE IA — HERRAMIENTAS DE DATOS (SQL solo-lectura + RESUMEN)
# ==================================================================
import re as _re

# Catálogo de esquema ACOTADO que se inyecta al modelo para que genere SQL
# aterrizado. Solo tablas de Betplay + maestros (no todo el diccionario de la BD).
ASSISTANT_SCHEMA_CATALOG = """ESQUEMA DISPONIBLE (Oracle). Solo puedes consultar estas tablas y columnas.
El mismo SELECT se ejecuta automáticamente en las dos bases (CAUCA y FORTUNA) y
sus filas se combinan agregando una columna "Fuente"; NO tienes que elegir base.

-- Betplay: PAGOS (retiros) --
GANA_SIGA.SIGT_PAGOS (alias P)
  IDE_PRODUCTO   number   -- Betplay pago = 17288
  IDE_SITIOVENTA number   -- FK a MAET_SITIOSVENTA.IDE_SITIOVENTA
  IDE_USUARIO    number   -- FK a MAET_USUARIOS.IDE_USUARIO
  FEC_PAGO       date     -- fecha/hora de la transacción
  VALOR_PAGO     number   -- monto en COP
  IDE_ESTADO     number   -- transacción válida = 264
  Filtro Betplay: IDE_PRODUCTO = 17288 AND IDE_ESTADO = 264

-- Betplay: RECARGAS --
GANA_SIGA.SIGT_RECARGAS (alias R)
  IDE_PRODUCTO   number   -- Betplay recarga = 17287
  IDE_SITIOVENTA number
  IDE_USUARIO    number
  FEC_VENTA      date
  VLR_RECARGA    number   -- monto en COP
  IDE_ESTADO     number   -- transacción válida = 48
  Filtro Betplay: IDE_PRODUCTO = 17287 AND IDE_ESTADO = 48

-- Maestros --
GANA_MAESTROS.MAET_USUARIOS (alias U)
  IDE_USUARIO number, NUM_IDENTIFICACION varchar  -- identificación del cliente
GANA_MAESTROS.MAET_SITIOSVENTA (alias SV)
  IDE_SITIOVENTA number, NOM_SITIOVENTA varchar, IDE_CIUDAD number,
  IDE_OFICINA number, IDE_TIPO_SITIO number, DIRECCION varchar,
  ACTIVO varchar, CX number, CY number
GANA_MAESTROS.MAET_CIUDADES (alias CIUDAD)
  IDE_CIUDAD number, NOM_CIUDAD varchar
GANA_MAESTROS.MAET_OFICINAS (alias OFICINA)
  IDE_OFICINA number, NOM_OFICINA varchar, IDE_SUBZONA number
GANA_MAESTROS.MAET_SUBZONAS (alias SUBZONA)
  IDE_SUBZONA number, NOM_SUBZONA varchar, IDE_ZONA number
GANA_MAESTROS.MAET_ZONAS (alias ZONA)
  IDE_ZONA number, NOM_ZONA varchar
GANA_MAESTROS.MAET_TIPOS_SITIOVENTA (alias TSV)
  IDE_TIPO_SITIO number, DES_TIPO_SITIO varchar

-- Joins geográficos habituales --
P.IDE_SITIOVENTA = SV.IDE_SITIOVENTA
SV.IDE_CIUDAD    = CIUDAD.IDE_CIUDAD
SV.IDE_OFICINA   = OFICINA.IDE_OFICINA
OFICINA.IDE_SUBZONA = SUBZONA.IDE_SUBZONA
SUBZONA.IDE_ZONA = ZONA.IDE_ZONA
SV.IDE_TIPO_SITIO = TSV.IDE_TIPO_SITIO
P.IDE_USUARIO    = U.IDE_USUARIO   (igual para R.IDE_USUARIO)

-- Consultas POR USUARIO / CLIENTE --
Puedes responder preguntas sobre un cliente concreto usando IDE_USUARIO (id interno) o
NUM_IDENTIFICACION (cédula/identificación del cliente). Une la transacción con MAET_USUARIOS:
  P.IDE_USUARIO = U.IDE_USUARIO   (igual para R.IDE_USUARIO)
Si el usuario da una identificación (cédula), filtra por U.NUM_IDENTIFICACION (es varchar, usa comillas).
Si da un id de usuario numérico, filtra por IDE_USUARIO directamente. Ejemplo (recargas de un cliente):
  SELECT U.NUM_IDENTIFICACION, COUNT(*) AS num, SUM(R.VLR_RECARGA) AS total
  FROM GANA_SIGA.SIGT_RECARGAS R
  JOIN GANA_MAESTROS.MAET_USUARIOS U ON R.IDE_USUARIO = U.IDE_USUARIO
  WHERE R.IDE_PRODUCTO = 17287 AND R.IDE_ESTADO = 48
    AND U.NUM_IDENTIFICACION = '1234567890'
  GROUP BY U.NUM_IDENTIFICACION

REGLAS SQL:
- Oracle. Fechas con TO_DATE('YYYY-MM-DD HH24:MI:SS','YYYY-MM-DD HH24:MI:SS') o TRUNC(SYSDATE) para hoy.
- Solo SELECT/WITH; una sola sentencia; sin punto y coma final.
- Limita SIEMPRE el resultado (FETCH FIRST N ROWS ONLY); si no lo pones, se acota automáticamente.
- Para consultas por cliente usa IDE_USUARIO o NUM_IDENTIFICACION (join con MAET_USUARIOS).
- No consultes tablas fuera de este catálogo."""

# Términos de escritura/DDL/DCL/PLSQL prohibidos (límites de palabra, case-insensitive)
_SQL_FORBIDDEN = _re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|"
    r"EXEC|EXECUTE|BEGIN|DECLARE|CALL|COMMIT|ROLLBACK|RENAME|INTO|SAVEPOINT|"
    r"LOCK|FLASHBACK|PURGE)\b",
    _re.IGNORECASE,
)
_ALLOWED_SQL_SCHEMAS = {"GANA_SIGA", "GANA_MAESTROS"}


def _validate_readonly_sql(sql):
    """
    Valida que `sql` sea una única sentencia de solo lectura sobre los esquemas
    permitidos. Devuelve (ok: bool, sql_saneado: str|None, error: str|None).
    Si falta un límite de filas, lo agrega (FETCH FIRST N ROWS ONLY).
    """
    if not sql or not sql.strip():
        return False, None, "SQL vacío."
    s = sql.strip()
    # Quitar un único ';' final si viene; múltiples sentencias => rechazo.
    if s.endswith(";"):
        s = s[:-1].rstrip()
    if ";" in s:
        return False, None, "Solo se permite una sentencia (sin ';' múltiples)."
    # Debe empezar por SELECT o WITH (permitiendo paréntesis iniciales).
    head = s.lstrip("( \t\r\n")
    if not _re.match(r"(?is)^(select|with)\b", head):
        return False, None, "La consulta debe empezar por SELECT o WITH."
    # Bloqueo de operaciones no-lectura.
    if _SQL_FORBIDDEN.search(s):
        return False, None, "La consulta contiene una operación no permitida (solo lectura)."
    # Whitelist de esquemas: toda tabla calificada tras FROM/JOIN debe estar en un
    # esquema permitido. Solo miramos FROM/JOIN para no confundir un esquema con un
    # alias de columna (p.ej. P.IDE_USUARIO en el SELECT).
    for m in _re.finditer(r"(?is)\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_$]*)\s*\.\s*[A-Za-z_]", s):
        schema = m.group(1).upper()
        if schema not in _ALLOWED_SQL_SCHEMAS:
            return False, None, f"Esquema no permitido: {schema}."
    # Forzar límite de filas si el modelo no lo puso.
    if not _re.search(r"(?is)\bfetch\s+first\b", s) and not _re.search(r"(?is)\brownum\b", s):
        s = f"{s}\nFETCH FIRST {LLM_SQL_ROW_LIMIT} ROWS ONLY"
    return True, s, None


def _run_assistant_sql(sql):
    """
    Valida y ejecuta el SELECT en CAUCA y FORTUNA (solo lectura), combina las
    filas etiquetando "Fuente" y recorta al tope de filas. Devuelve un dict
    apto para reinyectar como observación al modelo.
    """
    ok, clean, err = _validate_readonly_sql(sql)
    if not ok:
        return {"error": err, "sql": sql}

    rows_all = []
    per_source = {}
    errors = []
    for source, get_conn in (
        ("CAUCA", db_manager.get_cauca_connection),
        ("FORTUNA", db_manager.get_fortuna_connection),
    ):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(clean)
                    rows = rows_to_dicts(cur)
                    for r in rows:
                        r["Fuente"] = source
                    rows_all.extend(rows)
                    per_source[source] = len(rows)
        except Exception as e:
            logger.error(f"Assistant SQL failed on {source}: {e}")
            errors.append(f"{source}: {e}")

    total = len(rows_all)
    capped = rows_all[: LLM_SQL_ROW_LIMIT]
    return {
        "sql": clean,
        "columns": list(capped[0].keys()) if capped else [],
        "rows": capped,
        "row_count": total,
        "truncated": total > LLM_SQL_ROW_LIMIT,
        "per_source": per_source,
        "errors": errors,
    }


def _run_assistant_resumen(desde=None, hasta=None, tipo="ambos"):
    """
    Resumen agregado bajo demanda (pagos y/o recargas). Reutiliza el cálculo
    compacto existente. Se usa cuando la pregunta es genérica o al iniciar el
    chat, para dar una visión rápida del periodo (por defecto, el día actual).
    """
    today = date.today()
    desde = desde or f"{today.isoformat()} 00:00:00"
    hasta = hasta or f"{(today + timedelta(days=1)).isoformat()} 00:00:00"
    tipos = ["pagos", "recargas"] if (tipo or "ambos").lower() in ("ambos", "both", "todo") else [tipo.lower()]
    out = {"periodo": {"desde": desde, "hasta": hasta}}
    for t in tipos:
        if t in ("pagos", "recargas"):
            out[t] = _compact_resumen_for_context(t, desde, hasta)
    return out


# --- Herramienta web del asistente (búsqueda en internet) ---


def _run_web_search(query, max_results=None):
    """
    Búsqueda web general vía DuckDuckGo (librería `ddgs`, gratuita, sin API key).
    Devuelve una lista compacta de resultados [{titulo, cuerpo, url}]. Best-effort:
    ante error o timeout, devuelve {"error": ...} para reinyectar al modelo.
    """
    query = (query or "").strip()
    if not query:
        return {"error": "consulta vacía"}
    n = max_results or WEB_SEARCH_MAX_RESULTS
    try:
        from ddgs import DDGS
        resultados = []
        with DDGS(timeout=WEB_SEARCH_TIMEOUT) as ddgs:
            for r in ddgs.text(query, region="co-es", max_results=n):
                resultados.append({
                    "titulo": r.get("title"),
                    "cuerpo": (r.get("body") or "")[:400],
                    "url": r.get("href") or r.get("url"),
                })
        return {"query": query, "resultados": resultados, "total": len(resultados)}
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return {"error": str(e), "query": query}


@app.post("/api/assistant/upload")
async def assistant_upload(file: UploadFile = File(...)):
    """
    Procesa un PDF adjunto y devuelve su texto extraído (para inyectarlo como
    contexto en el chat). Solo PDFs: las imágenes se manejan en el cliente
    (base64) y solo se envían al modelo con visión.
    """
    raw = await file.read()
    if len(raw) > UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"El archivo supera el límite de {UPLOAD_MAX_BYTES // (1024*1024)} MB.")

    name = (file.filename or "").lower()
    if not name.endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Solo se aceptan archivos PDF en este endpoint.")

    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(raw))
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        texto = "\n".join(parts).strip()
    except Exception as e:
        logger.error(f"No se pudo extraer texto del PDF: {e}")
        raise HTTPException(status_code=422, detail="No se pudo leer el PDF.")

    truncated = len(texto) > PDF_TEXT_MAX_CHARS
    if truncated:
        texto = texto[:PDF_TEXT_MAX_CHARS]

    return {
        "filename": file.filename,
        "kind": "pdf",
        "chars": len(texto),
        "truncated": truncated,
        "escaneado": len(texto) < 40,  # casi sin texto => probablemente escaneado
        "texto": texto,
    }


ASSISTANT_SYSTEM_PROMPT = """Eres un asistente de análisis de datos para el producto Betplay de una empresa de apuestas y servicios.
Respondes y piensas/razonas SIEMPRE en español, de forma clara y concisa, orientado a la toma de decisiones.
Puedes usar Markdown (negritas con **texto**, listas con guiones, etc.).

NO tienes datos precargados. Para conocer cifras DEBES pedirlas usando una de estas dos HERRAMIENTAS.
Cuando emitas un bloque de herramienta, DETENTE inmediatamente y espera: el sistema lo ejecuta y te
devuelve el resultado en el siguiente turno; entonces continúas. Un solo bloque de herramienta por mensaje,
y no escribas nada importante después del bloque (se ignora).

HERRAMIENTA 1 — Consulta SQL (datos exactos / detalle). Emite un bloque ```sql con UN SOLO SELECT de solo lectura
sobre el ESQUEMA DISPONIBLE (ver más abajo). Ejemplo:
```sql
SELECT SUM(VALOR_PAGO) AS total FROM GANA_SIGA.SIGT_PAGOS
WHERE IDE_PRODUCTO = 17288 AND IDE_ESTADO = 264 AND TRUNC(FEC_PAGO) = TRUNC(SYSDATE)
```
El mismo SELECT se ejecuta en las dos bases (CAUCA y FORTUNA) y las filas se combinan con una columna "Fuente".

HERRAMIENTA 2 — Resumen agregado (visión rápida). Úsala cuando la pregunta sea GENÉRICA ("¿cómo va el día?",
"dame un resumen") o al INICIO de la conversación para un panorama. Emite un bloque ```resumen (vacío = día actual,
pagos y recargas). Opcionalmente un JSON con {"tipo":"pagos|recargas|ambos","desde":"YYYY-MM-DD HH:MM:SS","hasta":"..."}:
```resumen
{"tipo":"ambos"}
```
Devuelve totales, por hora, por zona, por ciudad, por oficina, top sitios y top usuarios del periodo.

HERRAMIENTA 3 — Búsqueda web (internet). Herramienta COMPLEMENTARIA y OPCIONAL. Es tu fuente para lo que
no está en la base de datos: sobre todo, qué partido de fútbol hubo en una fecha concreta.
Emite un bloque ```buscar con el texto de búsqueda (una línea):
```buscar
partidos de futbol 17 de junio de 2026 resultados
```
Devuelve una lista de resultados (título, extracto y URL). Cita la fuente cuando uses un dato web.

CUÁNDO usar la búsqueda web (sé conservador, NO abuses):
- Úsala cuando el USUARIO pida explícitamente la causa de un pico/valle o preguntes por eventos deportivos.
- Úsala también, de forma puntual, si al analizar una anomalía aporta valor saber qué fútbol hubo ese día.
- NO la uses para preguntas de puro dato interno (cuánto se vendió, top zona, etc.).
- Haz como MÁXIMO una búsqueda por fecha relevante y NO repitas búsquedas equivalentes. Si ya buscaste algo,
  no lo vuelvas a buscar con otras palabras: usa lo que ya obtuviste.

CÓMO buscar (para que traiga partidos y no páginas genéricas):
- UNA FECHA CONCRETA por consulta; NO combines varias fechas ni rangos.
- Usa la fórmula: "partidos de futbol <DÍA de MES de AÑO> resultados".
- NO uses "eventos deportivos", "festivos" ni "calendario": IGNORA los festivos.
- Fíjate en fútbol importante: Selección Colombia, clubes colombianos (Nacional, Millonarios, América,
  Junior), Champions League, Libertadores, Mundial, Copa América. Reporta el partido concreto (equipos y torneo).
- Correlaciona sin afirmar causalidad absoluta ("coincide con", "posiblemente por"). Si no hay partido claro,
  dilo con honestidad; no inventes eventos.

REGLAS DE DATOS:
- "monto" está en pesos colombianos (COP). Las cantidades son número de transacciones.
- No inventes cifras: si no tienes el dato, pídelo con una herramienta. Si tras consultarlo no aparece, dilo con honestidad.
- Máximo {MAX_ITERS} consultas por respuesta; sé eficiente (una consulta bien pensada mejor que muchas).
- Si un SQL devuelve error, corrígelo y reinténtalo respetando el esquema.

FORMA DE RESPONDER (importante):
- No sobrepienses. Para preguntas simples, directas o de un solo dato (por ejemplo "¿cuánto se vendió hoy?",
  "¿cuál fue la zona con más ventas?"), responde de forma directa y breve, sin razonamiento extenso.
  Reserva el análisis más elaborado para preguntas analíticas, comparativas o de proyección.
- Tienes LIBERTAD para enriquecer tus respuestas: cuando aporte valor, puedes agregar datos de apoyo,
  observaciones y conclusiones que ayuden a la toma de decisiones. Etiqueta claramente lo que es interpretación
  tuya (por ejemplo con "Observación:" o "Conclusión:") y no lo mezcles con las cifras exactas consultadas.
- EXCEPCIÓN: si el usuario pide EXPLÍCITAMENTE solo un dato o solo cierta información
  (por ejemplo "dame solo el total", "únicamente el número", "sin análisis"), entrega solo eso,
  sin observaciones ni conclusiones añadidas.

PROYECCIONES:
Si te piden un estimado/proyección de ventas del día, primero consulta el historial reciente con SQL
(por ejemplo, totales por día de los últimos días) y proyecta con base en eso (promedio de los mismos
días de la semana o tendencia). SIEMPRE que proyectes:
- Explica brevemente el método usado.
- Añade una nota clara: "Esta es una proyección estimada y subjetiva, no un valor garantizado."
- Ten en cuenta que el día actual puede estar incompleto (parcial hasta la hora actual).

GRÁFICOS Y TABLAS:
Cuando una visualización ayude a responder, puedes incluirla usando bloques de código cercados con un lenguaje especial.
El texto explicativo va FUERA de los bloques (antes o después). Usa JSON válido dentro del bloque.

Para un gráfico, usa un bloque ```chart con este formato exacto:
```chart
{"chart_type": "bar", "title": "Monto por zona", "x": ["Norte","Sur"], "series": [{"label": "Monto", "data": [3800000, 2100000]}]}
```
- chart_type puede ser: "bar", "horizontalBar", "line", "doughnut" o "pie".
- "x" son las etiquetas/categorías; cada serie tiene "label" y "data" (números alineados con "x").

Para una tabla, usa un bloque ```table con este formato exacto:
```table
{"columns": ["Sitio","Transacciones"], "rows": [["Puesto A", 15], ["Puesto B", 9]]}
```

Reglas:
- Genera un gráfico o tabla SOLO si aporta valor; no abuses.
- El JSON debe ser válido y completo (no lo cortes). Una sola visualización por bloque.
- NO generes dos gráficos (ni dos tablas) que muestren los MISMOS datos o el mismo resultado. Si ya
  visualizaste una serie, no la repitas con otro gráfico distinto: una sola visualización por idea.
- Acompaña la visualización con una breve explicación en texto, pero NO repitas los mismos datos dos veces:
  si usas un bloque ```table o ```chart, NO vuelvas a escribir esos datos como tabla Markdown ni los enumeres todos en texto.
- No generes em-dashes
- No responder con emojis 
"""


# --- Loop ReAct: detección de bloques de herramienta en el stream ---

# Bloque de herramienta COMPLETO: ```sql ... ``` o ```resumen ... ```
_TOOL_FENCE_RE = _re.compile(r"```(sql|resumen|buscar)[ \t]*\r?\n(.*?)```", _re.DOTALL | _re.IGNORECASE)

# Nombres de herramienta (para retención segura del stream y validación).
_TOOL_KINDS = ("sql", "resumen", "buscar")

# Marcadores de chip que el frontend interpreta (estado de las herramientas).
def _tool_chip(kind, estado, **meta):
    payload = {"kind": kind, "estado": estado}
    payload.update(meta)
    return "[[TOOL]]" + json.dumps(payload, ensure_ascii=False, default=str) + "[[/TOOL]]"


def _safe_flush_len(buf):
    """
    Índice hasta el que es seguro emitir `buf` como texto normal sin cortar por
    la mitad la apertura de un bloque de herramienta (```sql / ```resumen). Los
    bloques ```chart / ```table SÍ se dejan pasar (los renderiza el frontend).
    """
    idx = buf.rfind("```")
    if idx == -1:
        # Retener un run final de 1-2 backticks (posible inicio de ```).
        t = len(buf)
        while t > 0 and buf[t - 1] == "`" and (len(buf) - t) < 2:
            t -= 1
        return t
    nl = buf.find("\n", idx)
    if nl != -1:
        tag = buf[idx + 3:nl].strip().lower()
        # Herramienta abierta pero aún sin cerrar: retener hasta el cierre.
        return idx if tag in _TOOL_KINDS else len(buf)
    # Etiqueta aún llegando: retener si puede convertirse en una herramienta.
    tag = buf[idx + 3:].strip().lower()
    if tag == "" or any(k.startswith(tag) for k in _TOOL_KINDS):
        return idx
    return len(buf)


def _observation_text_sql(sql, result):
    """Texto de observación (resultado del SQL) que se reinyecta al modelo."""
    if result.get("error"):
        return f"ERROR al ejecutar el SQL (corrígelo y vuelve a intentar): {result['error']}"
    payload = {
        "columns": result.get("columns"),
        "rows": result.get("rows"),
        "per_source": result.get("per_source"),
    }
    header = f"RESULTADO SQL: {result.get('row_count', 0)} filas (mostrando {len(result.get('rows', []))})."
    if result.get("truncated"):
        header += f" Recortado a {LLM_SQL_ROW_LIMIT}."
    if result.get("errors"):
        header += " Advertencias: " + "; ".join(result["errors"])
    return header + "\n" + json.dumps(payload, ensure_ascii=False, default=str)


def _parse_resumen_params(body, def_desde, def_hasta):
    params = {"desde": def_desde, "hasta": def_hasta, "tipo": "ambos"}
    body = (body or "").strip()
    if body:
        try:
            j = json.loads(body)
            if isinstance(j, dict):
                params["tipo"] = j.get("tipo", params["tipo"])
                params["desde"] = j.get("desde", params["desde"])
                params["hasta"] = j.get("hasta", params["hasta"])
        except Exception:
            pass
    return params


class AssistantChatRequest(BaseModel):
    pregunta: str
    historial: Optional[List[dict]] = None  # [{role, content}, ...]
    desde: Optional[str] = None
    hasta: Optional[str] = None
    model: Optional[str] = None  # id del modelo elegido (catálogo amigable)
    # Adjuntos de la pregunta actual:
    #   pdf   -> {"kind":"pdf","filename":..., "texto":...}
    #   image -> {"kind":"image","filename":..., "data_url":"data:image/...;base64,..."}
    adjuntos: Optional[List[dict]] = None
    web_enabled: Optional[bool] = True  # permite/bloquea las herramientas de red


@app.post("/api/assistant/chat")
def assistant_chat(req: AssistantChatRequest):
    """
    Chat del asistente con streaming y loop ReAct: el modelo pide datos mediante
    bloques ```sql (SELECT solo-lectura, ejecutado en CAUCA+FORTUNA) o ```resumen
    (agregado del periodo). No se inyecta ningún resumen por defecto: el contexto
    es solo el catálogo de esquema y el periodo. La respuesta se transmite token a
    token (text/plain), pausando en cada herramienta para ejecutarla y continuar.
    """
    # Rango por defecto: día actual [hoy 00:00, mañana 00:00)
    today = date.today()
    desde = req.desde or f"{today.isoformat()} 00:00:00"
    hasta = req.hasta or f"{(today + timedelta(days=1)).isoformat()} 00:00:00"

    # Resolución del modelo (se hace antes de armar el mensaje porque las
    # imágenes solo se envían a modelos con visión):
    # - Si el usuario eligió uno del catálogo, se usa y se asegura su carga.
    # - Si NO hay selección explícita, se usa el modelo del catálogo que ya esté
    #   cargado. Solo si no hay ninguno cargado se recurre al configurado.
    if req.model in _ASSISTANT_MODEL_IDS:
        model_id = req.model
        ensure_model_loaded(model_id)
    else:
        loaded = _current_catalog_model()
        model_id = loaded or LLM_MODEL
        if loaded is None:
            ensure_model_loaded(model_id)

    tiene_vision = model_id in VISION_MODEL_IDS

    contexto = {"periodo_por_defecto": {"desde": desde, "hasta": hasta}, "hoy": today.isoformat()}
    system_prompt = ASSISTANT_SYSTEM_PROMPT.replace("{MAX_ITERS}", str(LLM_MAX_SQL_ITERS))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": ASSISTANT_SCHEMA_CATALOG},
        {"role": "system", "content": "CONTEXTO: " + json.dumps(contexto, ensure_ascii=False)},
    ]
    if req.historial:
        for m in req.historial[-8:]:  # limitar historial
            role = m.get("role")
            content = m.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    # Mensaje del usuario, enriquecido con adjuntos (PDF como texto, imágenes
    # como image_url solo si el modelo tiene visión).
    texto_usuario = req.pregunta
    imagenes = []
    if req.adjuntos:
        bloques_pdf = []
        for a in req.adjuntos:
            kind = (a or {}).get("kind")
            if kind == "pdf" and a.get("texto"):
                fn = a.get("filename") or "documento.pdf"
                bloques_pdf.append(f"--- Documento adjunto: {fn} ---\n{a['texto']}")
            elif kind == "image" and a.get("data_url"):
                if tiene_vision:
                    imagenes.append(a["data_url"])
                # Si no hay visión, la imagen se ignora silenciosamente
                # (el frontend ya avisa al usuario antes de enviar).
        if bloques_pdf:
            texto_usuario = (
                "Documentos adjuntos por el usuario (úsalos como contexto para responder):\n\n"
                + "\n\n".join(bloques_pdf)
                + "\n\n--- Pregunta ---\n"
                + req.pregunta
            )

    if imagenes:
        content = [{"type": "text", "text": texto_usuario}]
        for url in imagenes:
            content.append({"type": "image_url", "image_url": {"url": url}})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": texto_usuario})

    def token_stream():
        # Loop ReAct con streaming. En cada turno:
        #  - El razonamiento (reasoning_content) se transmite en vivo, envuelto en
        #    las etiquetas que el frontend ya sabe colapsar.
        #  - El contenido se transmite en vivo salvo cuando aparece un bloque de
        #    herramienta (```sql / ```resumen): al completarse se ejecuta, se emite
        #    un chip de estado, se reinyecta el resultado y se hace otro turno.
        #  Los bloques ```chart / ```table NO son herramientas: pasan tal cual.
        convo = list(messages)
        client = get_llm_client()
        # Presupuestos separados: datos (sql/resumen) vs. web (buscar).
        web_allowed = bool(WEB_SEARCH_ENABLED and req.web_enabled)
        sql_used = 0
        web_used = 0
        max_turns = LLM_MAX_SQL_ITERS + LLM_MAX_WEB_ITERS + 1
        try:
            for turn in range(max_turns):
                allow_tools = (sql_used < LLM_MAX_SQL_ITERS) or (web_used < LLM_MAX_WEB_ITERS)
                in_reasoning = False
                content_buf = ""
                sent = 0
                tool = None  # (kind, body, end_index)

                stream = client.chat.completions.create(
                    model=model_id, messages=convo, temperature=0.4, stream=True,
                )
                for chunk in stream:
                    try:
                        delta = chunk.choices[0].delta
                    except (AttributeError, IndexError):
                        continue
                    reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
                    content = getattr(delta, "content", None)
                    if reasoning:
                        if not in_reasoning:
                            in_reasoning = True
                            yield "<|channel>thought"
                        yield reasoning
                    if content:
                        if in_reasoning:
                            in_reasoning = False
                            yield "<channel|>"
                        content_buf += content
                        if allow_tools:
                            m = _TOOL_FENCE_RE.search(content_buf)
                            if m:
                                # Emitir el texto previo al bloque y capturar la herramienta.
                                if m.start() > sent:
                                    yield content_buf[sent:m.start()]
                                    sent = m.start()
                                tool = (m.group(1).lower(), m.group(2), m.end())
                                break
                            flush = _safe_flush_len(content_buf)
                            if flush > sent:
                                yield content_buf[sent:flush]
                                sent = flush
                        else:
                            # Sin más herramientas permitidas: transmitir todo en vivo.
                            yield content
                            sent = len(content_buf)
                if in_reasoning:
                    yield "<channel|>"
                try:
                    stream.close()
                except Exception:
                    pass

                if tool is None:
                    # Respuesta final: volcar lo que quede en el buffer.
                    if len(content_buf) > sent:
                        yield content_buf[sent:]
                    return

                kind, body, end_idx = tool
                # Registrar lo que produjo el modelo (incluido el bloque) en la conversación.
                convo.append({"role": "assistant", "content": content_buf[:end_idx]})

                if kind in ("sql", "resumen"):
                    # Presupuesto de datos.
                    if sql_used >= LLM_MAX_SQL_ITERS:
                        obs = "Límite de consultas de datos alcanzado. Responde ahora con lo disponible."
                    elif kind == "sql":
                        sql_used += 1
                        sql = body.strip()
                        yield _tool_chip("sql", "run")
                        result = _run_assistant_sql(sql)
                        # Muestra acotada de resultados para que el usuario valide.
                        sample_rows = result.get("rows", [])[:10]
                        yield _tool_chip("sql", "done",
                                         sql=result.get("sql", sql),
                                         rows=result.get("row_count", 0),
                                         error=result.get("error"),
                                         columns=result.get("columns", []),
                                         sample=sample_rows)
                        obs = _observation_text_sql(sql, result)
                    else:  # resumen
                        sql_used += 1
                        yield _tool_chip("resumen", "run")
                        params = _parse_resumen_params(body, desde, hasta)
                        try:
                            result = _run_assistant_resumen(**params)
                            obs = "RESULTADO RESUMEN (JSON):\n" + json.dumps(result, ensure_ascii=False, default=str)
                        except Exception as e:
                            logger.error(f"Assistant resumen failed: {e}")
                            obs = f"ERROR al calcular el resumen: {e}"
                        yield _tool_chip("resumen", "done")
                else:  # buscar (web)
                    if web_used >= LLM_MAX_WEB_ITERS:
                        obs = "Límite de búsquedas web alcanzado. Responde ahora con lo disponible."
                    else:
                        web_used += 1
                        query = body.strip()
                        yield _tool_chip("buscar", "run")
                        if not web_allowed:
                            obs = ("Búsqueda web deshabilitada (el usuario apagó el acceso a "
                                   "internet). Responde con los datos disponibles.")
                            yield _tool_chip("buscar", "done", query=query, error=True)
                        else:
                            result = _run_web_search(query)
                            err = result.get("error")
                            obs = ("ERROR en búsqueda web: " + err) if err else (
                                "RESULTADO BÚSQUEDA WEB (JSON):\n"
                                + json.dumps(result, ensure_ascii=False, default=str))
                            yield _tool_chip("buscar", "done",
                                             query=query,
                                             resultados=result.get("total", 0),
                                             items=result.get("resultados", []),
                                             error=err)

                convo.append({"role": "user", "content": obs})
                # Sin presupuesto restante en ninguna vía: empujar a responder ya.
                if sql_used >= LLM_MAX_SQL_ITERS and web_used >= LLM_MAX_WEB_ITERS:
                    convo.append({"role": "system",
                                  "content": "Ya no puedes pedir más datos. Responde ahora con la información disponible."})
        except Exception as e:
            logger.error(f"Assistant chat streaming failed: {e}")
            yield f"\n\n[Error al contactar el modelo: {e}]"

    return StreamingResponse(token_stream(), media_type="text/plain; charset=utf-8")


def _resolve_assistant_model(model):
    """Resuelve y asegura la carga del modelo (misma lógica que el chat)."""
    if model in _ASSISTANT_MODEL_IDS:
        ensure_model_loaded(model)
        return model
    loaded = _current_catalog_model()
    model_id = loaded or LLM_MODEL
    if loaded is None:
        ensure_model_loaded(model_id)
    return model_id


def _stream_assistant_tokens(messages, model_id, temperature=0.4):
    """Generador que streamea la respuesta del modelo, envolviendo el
    razonamiento en las etiquetas que el frontend sabe parsear."""
    in_reasoning = False
    try:
        client = get_llm_client()
        stream = client.chat.completions.create(
            model=model_id, messages=messages, temperature=temperature, stream=True,
        )
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
            except (AttributeError, IndexError):
                continue
            reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
            content = getattr(delta, "content", None)
            if reasoning:
                if not in_reasoning:
                    in_reasoning = True
                    yield "<|channel>thought"
                yield reasoning
            if content:
                if in_reasoning:
                    in_reasoning = False
                    yield "<channel|>"
                yield content
        if in_reasoning:
            yield "<channel|>"
    except Exception as e:
        logger.error(f"Assistant streaming failed: {e}")
        if in_reasoning:
            yield "<channel|>"
        yield f"\n\n[Error al contactar el modelo: {e}]"


REPORT_SYSTEM_PROMPT = """Eres un redactor de informes ejecutivos para el producto Betplay.
A partir de FUENTES (fragmentos de una conversación de análisis: preguntas del usuario y respuestas del asistente)
y un CATÁLOGO DE FIGURAS disponibles, redacta un informe profesional en español, claro y orientado a decisiones.

Estructura el informe con:
- Un título (encabezado con "# ").
- Una introducción breve que contextualice el análisis.
- Secciones de análisis (encabezados con "## ") que integren y redacten la información de las fuentes.
- Una sección final de "## Conclusiones" con hallazgos y recomendaciones accionables.

Sobre las FIGURAS:
- El catálogo lista figuras numeradas (Figura 1, Figura 2, ...) con su título.
- Cuando quieras que una figura aparezca en el informe, escribe en una LÍNEA APARTE exactamente el marcador: [[FIGURA:N]]
  (por ejemplo, una línea que contenga solo "[[FIGURA:1]]"). El sistema insertará ahí el gráfico o tabla real.
- Puedes referenciarla en el texto como "(ver Figura N)". Usa cada figura como máximo una vez.
- No escribas bloques de código ```chart o ```table; solo usa los marcadores [[FIGURA:N]].

Reglas:
- Usa SOLO la información de las fuentes; no inventes cifras nuevas.
- Redacta de forma fluida y profesional (no copies las preguntas ni el estilo de chat).
- Usa Markdown (encabezados #/##, negritas **, listas con guiones).
- No generes em-dashes. No uses emojis.
"""


class AssistantReportRequest(BaseModel):
    fuentes: List[dict]          # [{rol:'user'|'assistant', texto:'...'}]
    figuras: Optional[List[dict]] = None  # [{n, tipo:'chart'|'table', titulo}]
    titulo: Optional[str] = None
    model: Optional[str] = None


@app.post("/api/assistant/report")
def assistant_report(req: AssistantReportRequest):
    """
    Segundo pase del modelo: toma mensajes seleccionados como fuentes y redacta
    un informe ejecutivo (con marcadores [[FIGURA:N]] para intercalar figuras).
    Devuelve el texto en streaming.
    """
    model_id = _resolve_assistant_model(req.model)

    fuentes_txt = []
    for i, f in enumerate(req.fuentes or [], 1):
        rol = "Usuario" if (f or {}).get("rol") == "user" else "Asistente"
        texto = (f or {}).get("texto", "")
        fuentes_txt.append(f"[Fuente {i} - {rol}]\n{texto}")

    figuras_txt = []
    for fig in (req.figuras or []):
        n = fig.get("n")
        tipo = "gráfico" if fig.get("tipo") == "chart" else "tabla"
        titulo = fig.get("titulo") or f"Figura {n}"
        figuras_txt.append(f"- Figura {n} ({tipo}): {titulo}")

    partes = ["FUENTES:\n" + "\n\n".join(fuentes_txt)]
    if figuras_txt:
        partes.append("CATÁLOGO DE FIGURAS:\n" + "\n".join(figuras_txt))
    else:
        partes.append("CATÁLOGO DE FIGURAS: (ninguna)")
    if req.titulo:
        partes.append(f"El usuario sugiere este título: {req.titulo}")
    partes.append("Redacta el informe ahora.")

    messages = [
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(partes)},
    ]

    return StreamingResponse(
        _stream_assistant_tokens(messages, model_id, temperature=0.5),
        media_type="text/plain; charset=utf-8",
    )

# ============================ ASISTENTE IA ============================

@app.post("/api/upload/metas")
async def upload_metas(
    files: List[UploadFile] = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Saves and parses multiple Excel files of daily goals.
    Uses filename or header content to distinguish between products.
    """
    logger.info(f"Received request to upload {len(files)} goals files.")
    global goals_store
    
    parsed_files = []
    total_records = 0
    
    for f in files:
        file_path = os.path.join(UPLOAD_DIR, f.filename)
        # Write to disk
        with open(file_path, "wb") as buffer:
            buffer.write(await f.read())
            
        try:
            records = parse_metas_excel(file_path)
            if records:
                # Group by Excel product identifier
                product_excel = records[0]["producto_excel"]
                goals_store[product_excel] = records
                total_records += len(records)
                parsed_files.append({
                    "filename": f.filename,
                    "detected_product": product_excel,
                    "records_count": len(records)
                })
        except Exception as e:
            logger.error(f"Error parsing file {f.filename}: {e}")
            raise HTTPException(status_code=400, detail=f"Error parsing file {f.filename}: {str(e)}")
            
    # Persist in-memory store to JSON
    try:
        with open(GOALS_FILE, "w", encoding="utf-8") as out:
            json.dump(goals_store, out, ensure_ascii=False, indent=2)
        logger.info("Successfully persisted goals store to JSON.")
    except Exception as e:
        logger.error(f"Failed to persist goals store: {e}")

    return {
        "status": "success",
        "parsed_files": parsed_files,
        "total_records": total_records,
        "current_products": list(goals_store.keys())
    }

@app.post("/api/upload/distribucion")
async def upload_distribucion(file: UploadFile = File(...), current_user: CurrentUser = Depends(get_current_user)):
    """
    Saves and parses the promoter distribution Excel file.
    """
    logger.info(f"Received promoter distribution file: {file.filename}")
    global distribution_store
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    try:
        records = parse_promoters_excel(file_path)
        distribution_store = records
        
        # Persist to JSON
        with open(DISTRIBUTION_FILE, "w", encoding="utf-8") as out:
            json.dump(distribution_store, out, ensure_ascii=False, indent=2)
            
        return {
            "status": "success",
            "filename": file.filename,
            "records_count": len(records)
        }
    except Exception as e:
        logger.error(f"Error parsing promoters file: {e}")
        raise HTTPException(status_code=400, detail=f"Error parsing promoters file: {str(e)}")

@app.get("/api/metas")
def get_metas(
    fecha: Optional[str] = Query(None, description="Filtrar por fecha YYYY-MM-DD"),
    current_user: CurrentUser = Depends(get_current_user),
):
    flat_goals = []
    for prod, records in goals_store.items():
        if records and not records[0].get("activo", True):
            continue
        if fecha:
            flat_goals.extend([r for r in records if r.get("fecha") == fecha])
        else:
            flat_goals.extend(records)
    return flat_goals

class ToggleProductSchema(BaseModel):
    producto: str
    activo: bool

@app.get("/api/metas/products")
def get_metas_products(current_user: CurrentUser = Depends(get_current_user)):
    result = []
    for prod, records in goals_store.items():
        active = True
        if records:
            active = records[0].get("activo", True)
        result.append({
            "producto": prod,
            "count": len(records),
            "activo": active
        })
    return result

@app.post("/api/metas/toggle")
def toggle_product_goals(data: ToggleProductSchema, current_user: CurrentUser = Depends(get_current_user)):
    if data.producto in goals_store:
        for rec in goals_store[data.producto]:
            rec["activo"] = data.activo
        # Persist
        try:
            with open(GOALS_FILE, "w", encoding="utf-8") as f:
                json.dump(goals_store, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving goals: {e}")
        return {"status": "success", "producto": data.producto, "activo": data.activo}
    raise HTTPException(status_code=404, detail="Producto no encontrado")

@app.delete("/api/metas/product/{product_name}")
def delete_product_goals(product_name: str, current_user: CurrentUser = Depends(get_current_user)):
    if product_name in goals_store:
        goals_store.pop(product_name)
        # Persist
        try:
            with open(GOALS_FILE, "w", encoding="utf-8") as f:
                json.dump(goals_store, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving goals: {e}")
        return {"status": "success", "message": f"Metas de {product_name} eliminadas"}
    raise HTTPException(status_code=404, detail="Producto no encontrado")

@app.get("/api/distribucion")
def get_distribucion(current_user: CurrentUser = Depends(get_current_user)):
    return distribution_store

@app.post("/api/clear")
def clear_data(current_user: CurrentUser = Depends(get_current_user)):
    """Clears uploaded excels, saved JSONs, and local cache"""
    global goals_store, distribution_store
    goals_store = {}
    distribution_store = []
    
    if os.path.exists(GOALS_FILE):
        os.remove(GOALS_FILE)
    if os.path.exists(DISTRIBUTION_FILE):
        os.remove(DISTRIBUTION_FILE)
        
    try:
        clear_cache()
    except Exception as e:
        logger.error(f"Failed to clear SQLite cache: {e}")
        
    return {"status": "success", "message": "All uploaded data and local cache cleared. "}


# ==========================================
# WHATSAPP CLOUD API WEBHOOKS
# ==========================================

@app.get("/api/whatsapp/webhook")
def verify_whatsapp_webhook(
    mode: str = Query(None, alias="hub.mode"),
    challenge: str = Query(None, alias="hub.challenge"),
    token: str = Query(None, alias="hub.verify_token")
):
    """
    Endpoint for Meta WhatsApp Cloud API Webhook Verification.
    """
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "la_fortuna_token_2026")
    if mode == "subscribe" and token == verify_token:
        logger.info("Webhook verified successfully by Meta.")
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=challenge, status_code=200)
    logger.warning(f"Webhook verification failed. Token mismatch: expected '{verify_token}', got '{token}'")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/api/whatsapp/webhook")
async def receive_whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives incoming WhatsApp messages from Meta.

    Responde 200 de inmediato y procesa/envia la respuesta en segundo plano.
    Esto evita que Meta reintente la entrega del mismo mensaje (lo que causaba
    respuestas duplicadas cuando el procesamiento tardaba en responder).
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Error parsing Webhook JSON body: {e}")
        return {"status": "error", "message": "Invalid JSON"}

    logger.info(f"Received WhatsApp webhook notification: {json.dumps(body)}")

    # Modo simulacion: con ?dry_run=1 se ejecuta toda la logica real
    # (deteccion de primer contacto, ruteo por rol, recopilatorio de ayer,
    # botones) pero NO se envia nada por Meta; se devuelven los mensajes
    # compuestos para inspeccionarlos localmente. Debe ser sincrono para
    # poder devolver los mensajes compuestos en la respuesta.
    dry_run = str(request.query_params.get("dry_run", "")).lower() in {"1", "true", "yes"}
    if dry_run:
        return _process_whatsapp_message(body, dry_run=True)

    # Ruta real: responder 200 ya y enviar en segundo plano.
    background_tasks.add_task(_process_whatsapp_message, body, False)
    return {"status": "received"}


def _process_whatsapp_message(body: dict, dry_run: bool = False):
    """
    Procesa un mensaje entrante de WhatsApp: consulta la cache de ventas,
    compone la respuesta segun el rol y la envia via Meta's Cloud API.

    En dry_run no envia nada; devuelve los mensajes compuestos.
    """
    dry_messages = []

    # 1. Parse incoming message structures
    entry = body.get("entry", [])
    if not entry:
        return {"status": "ignored", "reason": "No entry field"}
        
    changes = entry[0].get("changes", [])
    if not changes:
        return {"status": "ignored", "reason": "No changes field"}
        
    value = changes[0].get("value", {})
    messages = value.get("messages", [])
    if not messages:
        # Ignore notifications like sent/delivered/read
        return {"status": "ignored", "reason": "No messages array (likely status update)"}
        
    message = messages[0]
    sender_phone = message.get("from") # E.g., "573108723207"
    if not sender_phone:
        return {"status": "error", "message": "No sender phone found"}
        
    # Check if the incoming message is an interactive button click or text query
    user_msg_text = ""
    message_type = message.get("type")
    if message_type == "text":
        text_obj = message.get("text", {})
        user_msg_text = text_obj.get("body", "").strip()
        
    session_key = f"session_{sender_phone}"
    session_data, _ = get_cached_sales(session_key)

    report_type = "products"
    selected_product = None
    query_result = None

    # Primer contacto del día: usamos la ventana de tiempo para ofrecer el reporte
    # del día anterior automáticamente a cualquier consulta en esos primeros minutos.
    first_session = is_first_session_of_day(sender_phone)
    ref_date_param = (date.today() - timedelta(days=1)).isoformat() if first_session else None

    # 2. Check user role
    administrator = find_active_administrator_by_phone(sender_phone)
    promoter = None
    coordinator = None
    if not administrator:
        promoter = find_active_promoter_by_phone(sender_phone)
        if not promoter:
            coordinator = find_active_coordinator_by_phone(sender_phone)
        
    # Check if the user is replying to a prompt (state machine)
    if administrator:
        # Administrator Session Routing
        report_type = "products" # Default to general report
        button_id = None
        if message_type == "interactive":
            interactive = message.get("interactive", {})
            button_reply = interactive.get("button_reply", {})
            button_id = button_reply.get("id")
            
        user_msg_lower = user_msg_text.lower()
        
        if (button_id == "view_general_report" or 
            any(keyword in user_msg_lower for keyword in ["general", "menu", "menú", "hola"])):
            report_type = "products"
        elif button_id == "view_coordinators_summary" or "coordinador" in user_msg_lower:
            report_type = "coordinators"
        elif user_msg_text.isdigit():
            report_type = "administrator_coordinator_detail"
            query_result = get_whatsapp_query(sender_phone, report_type=report_type, selected_product=user_msg_text, ref_date=ref_date_param)

        if query_result is None:
            query_result = get_whatsapp_query(sender_phone, report_type=report_type, ref_date=ref_date_param)
    elif coordinator:
        # Coordinator Session Routing
        report_type = "products" # Default to zone report
        button_id = None
        if message_type == "interactive":
            interactive = message.get("interactive", {})
            button_reply = interactive.get("button_reply", {})
            button_id = button_reply.get("id")
            
        user_msg_lower = user_msg_text.lower()
        
        if (button_id == "view_zone_report" or 
            any(keyword in user_msg_lower for keyword in ["zona", "menu", "menú", "hola"])):
            report_type = "products"
        elif button_id == "view_promoter_summary" or "promotor" in user_msg_lower:
            report_type = "prompt_promoter"
        elif user_msg_text.isdigit():
            report_type = "coordinator_promoter_detail"
            query_result = get_whatsapp_query(sender_phone, report_type=report_type, selected_product=user_msg_text, ref_date=ref_date_param)

        if query_result is None:
            query_result = get_whatsapp_query(sender_phone, report_type=report_type, ref_date=ref_date_param)
    else:
        # Promoter Session Routing
        if (session_data and isinstance(session_data, dict) and 
            session_data.get("state") == "awaiting_product_selection" and 
            message_type == "text" and 
            not any(keyword in user_msg_text.lower() for keyword in ["oficina", "producto", "hola", "menu", "menú"])):
            
            if user_msg_text.isdigit():
                num = int(user_msg_text)
                active_products = sorted([p for p, recs in goals_store.items() if recs and recs[0].get("activo", True)])
                if 1 <= num <= len(active_products):
                    selected_product = active_products[num - 1]
                    set_cached_sales(session_key, {"state": "idle"})
                    report_type = "product_office"
                    query_result = get_whatsapp_query(sender_phone, report_type=report_type, selected_product=selected_product, ref_date=ref_date_param)
                else:
                    reply_text = f"❌ Número inválido. Por favor escribe un número entre 1 y {len(active_products)}."
                    query_result = {"text": reply_text}
            else:
                active_products = sorted([p for p, recs in goals_store.items() if recs and recs[0].get("activo", True)])
                reply_text = f"⚠️ Por favor escribe únicamente el número del producto (1-{len(active_products)}) o escribe *menu* para cancelar."
                query_result = {"text": reply_text}
                
        else:
            # Normal routing for promoter
            if message_type == "interactive":
                interactive = message.get("interactive", {})
                button_reply = interactive.get("button_reply", {})
                button_id = button_reply.get("id")
                set_cached_sales(session_key, {"state": "idle"})
                
                if button_id == "view_product_report":
                    report_type = "products"
                elif button_id == "view_prod_office_report":
                    report_type = "prompt_product"
                    set_cached_sales(session_key, {"state": "awaiting_product_selection"})
            else:
                user_msg_lower = user_msg_text.lower()
                if "producto / oficina" in user_msg_lower or "producto/oficina" in user_msg_lower:
                    report_type = "prompt_product"
                    set_cached_sales(session_key, {"state": "awaiting_product_selection"})
                elif "producto" in user_msg_lower or "menu" in user_msg_lower or "menú" in user_msg_lower or "hola" in user_msg_lower:
                    set_cached_sales(session_key, {"state": "idle"})
                    report_type = "products"
                    
            if query_result is None:
                query_result = get_whatsapp_query(sender_phone, report_type=report_type, selected_product=selected_product, ref_date=ref_date_param)

    reply_text = query_result.get("text", "❌ Error al procesar consulta.")

    # 3. Reply to sender via Meta's Graph API
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    # Retrieve the phone number ID of the bot receiving the message
    phone_number_id = value.get("metadata", {}).get("phone_number_id")
    
    if not whatsapp_token and not dry_run:
        logger.error("WHATSAPP_TOKEN not configured in .env!")
        return {"status": "error", "message": "WHATSAPP_TOKEN not configured"}

    if not phone_number_id and not dry_run:
        logger.error("phone_number_id not found in webhook metadata!")
        return {"status": "error", "message": "phone_number_id not found"}
        
    import urllib.request
    import urllib.error
    
    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"

    # 1. Send the main report as a standard text message (limit 4096 characters, no error 400)
    if dry_run:
        dry_messages.append({"kind": "text", "label": "reporte_hoy", "text": reply_text})

    payload_text = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": sender_phone,
        "type": "text",
        "text": {
            "body": reply_text
        }
    }

    req_data_text = json.dumps(payload_text).encode("utf-8")
    req_text = urllib.request.Request(
        url,
        data=req_data_text,
        headers={
            "Authorization": f"Bearer {whatsapp_token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    if not dry_run:
        try:
            with urllib.request.urlopen(req_text) as response:
                res_body = response.read().decode("utf-8")
                logger.info(f"WhatsApp text report sent successfully to {sender_phone}: {res_body}")
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode("utf-8")
            logger.error(f"HTTPError sending text report to WhatsApp API: {he.code} - {err_msg}")
            return {"status": "error", "code": he.code, "message": err_msg}
        except Exception as e:
            logger.error(f"Unexpected error sending text report to WhatsApp API: {e}")
            return {"status": "error", "message": str(e)}

    # 2. Send the interactive menu buttons as a separate short message (limit 1024 characters, completely safe)
    buttons = []
    button_prompt = ""
    
    if query_result.get("is_administrator") is True:
        res_report_type = query_result.get("report_type")
        if res_report_type == "administrator_general":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_coordinators_summary",
                    "title": "Ver Coordinadores"
                }
            })
            button_prompt = "🔍 ¿Deseas ver el cumplimiento de los coordinadores?"
        elif res_report_type == "coordinators_summary":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_general_report",
                    "title": "Reporte General"
                }
            })
            from backend.cache import get_all_coordinators
            all_coors = get_all_coordinators()
            active_coors_sorted = sorted([c for c in all_coors if c.get("active", 1)], key=lambda x: x["name"])
            
            button_prompt = "🔢 *Lista de Coordinadores:*\n"
            for idx, c in enumerate(active_coors_sorted, 1):
                button_prompt += f"*{idx}.* {c['name']}\n"
            button_prompt += "\nEscribe el número del coordinador, o selecciona una opción:"
        elif res_report_type == "administrator_coordinator_products_view":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_coordinators_summary",
                    "title": "Ver Coordinadores"
                }
            })
            button_prompt = "📦 Selecciona una opción:"

    elif query_result.get("is_coordinator") is True:
        res_report_type = query_result.get("report_type")
        if res_report_type == "coordinator_general":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_promoter_summary",
                    "title": "Ver Promotores"
                }
            })
            button_prompt = "🔍 ¿Deseas ver el cumplimiento general de cada promotor?"
        elif res_report_type == "prompt_promoter":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_zone_report",
                    "title": "Reporte de Zona"
                }
            })
            promoter_list = query_result.get("promoter_list", [])
            if promoter_list:
                button_prompt = "🔢 *Lista de Promotores:*\n"
                for i, p in enumerate(promoter_list, 1):
                    button_prompt += f"*{i}.* {p[0]}\n"
                button_prompt += "\nEscribe el número del promotor, o selecciona una opción:"
            else:
                button_prompt = "📦 Seleccione una opción:"
        elif res_report_type == "coordinator_promoter_offices_view":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_promoter_summary",
                    "title": "Ver Promotores"
                }
            })
            button_prompt = "📦 Seleccione una opción:"
            
    elif "promoter" in query_result:
        res_report_type = query_result.get("report_type")
        if res_report_type == "products":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_prod_office_report",
                    "title": "Producto / Oficina"
                }
            })
            button_prompt = "🔍 ¿Deseas ver el detalle de un producto por oficina?"
        elif res_report_type == "product_office":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_product_report",
                    "title": "Reporte Productos"
                }
            })
            button_prompt = "📦 Seleccione una opción:"
            
    if buttons and dry_run:
        dry_messages.append({
            "kind": "interactive",
            "label": "menu_botones",
            "text": button_prompt,
            "buttons": [b["reply"]["title"] for b in buttons],
        })
    elif buttons:
        payload_buttons = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": sender_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": button_prompt
                },
                "action": {
                    "buttons": buttons
                }
            }
        }

        req_data_buttons = json.dumps(payload_buttons).encode("utf-8")
        req_buttons = urllib.request.Request(
            url,
            data=req_data_buttons,
            headers={
                "Authorization": f"Bearer {whatsapp_token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req_buttons) as response:
                res_body = response.read().decode("utf-8")
                logger.info(f"WhatsApp interactive buttons sent successfully to {sender_phone}: {res_body}")
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode("utf-8")
            logger.error(f"HTTPError sending interactive buttons to WhatsApp API: {he.code} - {err_msg}")
        except Exception as e:
            logger.error(f"Unexpected error sending interactive buttons to WhatsApp API: {e}")

    if dry_run:
        return {"status": "dry_run", "count": len(dry_messages), "messages": dry_messages}

    return {"status": "success", "message": "Reply and menus processed"}


# Serve Frontend Static files
frontend_dir = os.path.join(BASE_DIR, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    logger.warning("Frontend directory not found. API only mode active.")

# Trigger reload comment 2
