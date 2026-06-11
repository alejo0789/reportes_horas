import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.db import db_manager
from backend.queries import VENTAS_POR_HORA_QUERY, SITIOS_VENTA_QUERY, PRODUCTOS_QUERY
from backend.excel_parser import parse_metas_excel, parse_promoters_excel
from backend.cache import (
    init_cache_db, get_cached_sales, set_cached_sales, clear_cache,
    seed_promoters_from_excel, get_all_promoters, add_promoter, update_promoter, delete_promoter,
    find_active_promoter_by_phone,
    seed_coordinators, get_all_coordinators, add_coordinator, update_coordinator, delete_coordinator,
    find_active_coordinator_by_phone
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
        "distribution_records_count": len(distribution_store)
    }

@app.get("/api/ventas")
def get_ventas(
    desde: str = Query(..., description="Fecha inicio YYYY-MM-DD HH:MM:SS"),
    hasta: str = Query(..., description="Fecha fin YYYY-MM-DD HH:MM:SS"),
    force_refresh: bool = Query(False, description="Forzar consulta a Oracle y refrescar caché")
):
    """
    Executes the main hourly sales query on CAUCAMED and FORTUMED.
    Uses SQLite database for local caching to reduce load on Oracle and load instantly.
    If database queries fail but cache is present, falls back to cache.
    """
    cache_key = f"{desde}_{hasta}"
    
    # 1. Check local SQLite cache first if not forcing refresh
    cached_data, last_updated = get_cached_sales(cache_key)
    
    if cached_data is not None and not force_refresh:
        # Check if the cache has expired (only for TODAY, historical data NEVER expires)
        today_str = date.today().strftime("%Y-%m-%d")
        is_today = desde.startswith(today_str)
        
        cache_valid = True
        if is_today:
            try:
                dt_updated = datetime.fromisoformat(last_updated)
                # Expire after 1 hour
                if datetime.now() - dt_updated > timedelta(hours=1):
                    cache_valid = False
            except Exception:
                cache_valid = False
        
        if cache_valid:
            logger.info(f"Serving sales data from SQLite Cache for key {cache_key} (updated: {last_updated}).")
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

    # 3. Fallback to cache if database fails/is incomplete but we have stale cache
    if (db_failures or not results) and cached_data is not None:
        logger.warning(f"Database query failed or is incomplete. Errors: {errors}. Serving stale SQLite Cache.")
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
    desde: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD HH:MM:SS"),
    hasta: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD HH:MM:SS")
):
    """
    Endpoint for external schedulers (like n8n) to force update the SQLite cache.
    """
    if not desde or not hasta:
        today_str = datetime.now().strftime("%Y-%m-%d")
        desde = desde or f"{today_str} 00:00:00"
        hasta = hasta or f"{today_str} 23:59:59"
    logger.info(f"Forced refresh request received via API for range: {desde} to {hasta}")
    return get_ventas(desde=desde, hasta=hasta, force_refresh=True)


# Pydantic models for WhatsApp Promoters
class PromoterSchema(BaseModel):
    name: str
    zone: str
    phone: str
    active: int = 1

@app.get("/api/whatsapp-promoters")
def get_whatsapp_promoters_endpoint():
    """
    Returns list of all promoters in the whatsapp_promoters table.
    """
    return get_all_promoters()

@app.post("/api/whatsapp-promoters")
def create_whatsapp_promoter(p: PromoterSchema):
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
def update_whatsapp_promoter(pid: int, p: PromoterSchema):
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
def delete_whatsapp_promoter(pid: int):
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

@app.get("/api/whatsapp-coordinators")
def get_whatsapp_coordinators_endpoint():
    """
    Returns list of all coordinators in the whatsapp_coordinators table.
    """
    return get_all_coordinators()

@app.post("/api/whatsapp-coordinators")
def create_whatsapp_coordinator(c: CoordinatorSchema):
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
def update_whatsapp_coordinator(cid: int, c: CoordinatorSchema):
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
def delete_whatsapp_coordinator(cid: int):
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
    override_promoter_name: Optional[str] = Query(None, description="Nombre de promotor para consulta por coordinador")
):
    # Resolve FastAPI Query defaults if called directly in Python
    if not isinstance(selected_product, str):
        selected_product = None
    if not isinstance(override_promoter_name, str):
        override_promoter_name = None
    if not isinstance(phone, str):
        phone = None
    if not isinstance(report_type, str):
        report_type = "products"

    # 1. Buscar promotor o coordinador por celular
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
    else:
        if not phone:
            return {"text": "❌ Falta número de teléfono o nombre para la consulta."}
        promoter = find_active_promoter_by_phone(phone)
        coordinator = None
        if not promoter:
            coordinator = find_active_coordinator_by_phone(phone)
            
        if not promoter and not coordinator:
            return {
                "text": "❌ Lo sentimos, tu número de celular no está registrado o no se encuentra activo para consultas por WhatsApp."
            }
            
        user_name = promoter["name"] if promoter else coordinator["name"]
        is_coordinator = coordinator is not None
        user_label = "Coordinador" if is_coordinator else "Promotor"
        user_zone = coordinator["zone"] if is_coordinator else promoter["zone"]
    
    # 2. Encontrar oficinas asignadas en la distribución comercial
    assigned_offices = set()
    if is_coordinator:
        for item in distribution_store:
            item_zone = item.get("zona", "")
            if item_zone and str(item_zone).strip().lower() == user_zone.strip().lower():
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

    # Calculate individual promoter metrics in coordinator's zone
    promoter_compliance_list = []
    if is_coordinator and report_type in {"products", "offices"}:
        promoter_to_offices = {}
        for item in distribution_store:
            item_zone = item.get("zona", "")
            if item_zone and item_zone.strip().lower() == user_zone.strip().lower():
                p_name = item.get("promotor")
                off = item.get("cod_oficina")
                if p_name and off is not None:
                    try:
                        off_int = int(off)
                        if p_name not in promoter_to_offices:
                            promoter_to_offices[p_name] = set()
                        promoter_to_offices[p_name].add(off_int)
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
                    
        products_data, _ = get_cached_sales("catalog_productos")
        products_by_code = {}
        if products_data:
            for p in products_data:
                cod = p.get("Cod_Producto")
                if cod is not None:
                    products_by_code[str(cod)] = p
                    
        today_str = datetime.now().strftime("%Y-%m-%d")
        desde = f"{today_str} 00:00:00"
        hasta = f"{today_str} 23:59:59"
        
        sales_list = []
        try:
            sales_resp = get_ventas(desde=desde, hasta=hasta, force_refresh=False)
            sales_list = sales_resp.get("data", [])
        except:
            pass
            
        for p_name, p_offices in promoter_to_offices.items():
            p_sales = 0.0
            for sale in sales_list:
                src_table = sale.get("Tabla_Origen")
                s_code = sale.get("Cod_Producto")
                if src_table in {'SIGT_SG_GIROS_PAGADOS', 'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
                    continue
                if src_table == 'SIGT_RECAUDOS_MAESTRO' and str(s_code) != '22005':
                    continue
                s_code = sale.get("Cod_Sitio")
                if s_code is not None:
                    try:
                        s_code_int = int(s_code)
                        off_code = site_to_office.get(s_code_int)
                        if off_code in p_offices:
                            v_neta = float(sale.get("Venta_Neta") or 0.0)
                            prod_name = resolve_product_name(sale, products_by_code)
                            is_count_based = prod_name in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
                            p_sales += 1.0 if is_count_based else v_neta
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
            promoter_compliance_list.append((p_name, p_sales, p_meta, p_comp))
            
        promoter_compliance_list.sort(key=lambda x: x[0])

    # Early return for prompt_promoter
    if is_coordinator and report_type == "prompt_promoter":
        zone_promoters = sorted(list(set([
            item.get("promotor") for item in distribution_store 
            if item.get("zona", "").strip().lower() == user_zone.strip().lower() and item.get("promotor")
        ])))
        if not zone_promoters:
            return {
                "text": "⚠️ No hay promotores asignados a tu zona en la distribución comercial.",
                "report_type": "prompt_promoter",
                "is_coordinator": True
            }
        msg = f"🔢 *Seleccione un promotor para ver su detalle por producto:*\n\n"
        for idx, prom in enumerate(zone_promoters, 1):
            msg += f"*{idx}.* {prom}\n"
        msg += f"\nPor favor, escribe el *número* del promotor que deseas consultar."
        return {
            "text": msg,
            "report_type": "prompt_promoter",
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

    # Load products catalog to map cod_producto to product info (same as frontend app.js)
    products_data, _ = get_cached_sales("catalog_productos")
    products_by_code = {}
    if products_data:
        for p in products_data:
            cod = p.get("Cod_Producto")
            if cod is not None:
                products_by_code[str(cod)] = p
                
    # 4. Obtener ventas del día de hoy
    today_str = datetime.now().strftime("%Y-%m-%d")
    desde = f"{today_str} 00:00:00"
    hasta = f"{today_str} 23:59:59"
    
    sales_list = []
    try:
        sales_resp = get_ventas(desde=desde, hasta=hasta, force_refresh=False)
        sales_list = sales_resp.get("data", [])
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
        if src_table in {'SIGT_SG_GIROS_PAGADOS', 'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
            continue
        if src_table == 'SIGT_RECAUDOS_MAESTRO' and str(s_code) != '22005':
            continue

        s_code = sale.get("Cod_Sitio")
        if s_code is not None:
            try:
                s_code_int = int(s_code)
                off_code = site_to_office.get(s_code_int)
                if off_code in assigned_offices:
                    v_neta = float(sale.get("Venta_Neta") or 0.0)
                    prod_name = resolve_product_name(sale, products_by_code)
                    
                    # Filtro para reporte producto/oficina
                    if report_type == "product_office" and prod_name != selected_product:
                        continue
                        
                    # Measured by transaction count (increment of 1) for specific products
                    is_count_based = prod_name in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
                    increment = 1.0 if is_count_based else v_neta
                    
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
                        if off_code_int in assigned_offices:
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
    
    if is_coordinator and report_type in {"products", "offices"}:
        msg = f"📊 *REPORTE DE ZONA (GENERAL)*\n"
        msg += f"👤 *Coordinador:* {user_name}\n"
        msg += f"📅 *Fecha:* {today_str}\n"
        msg += f"📍 *Zona:* {user_zone}\n"
        msg += f"──────────────────\n"
        msg += f"💰 *Venta Acumulada:* ${round(total_sales):,}\n"
        msg += f"🎯 *Meta Total:* ${round(total_goals):,}\n"
        msg += f"📈 *Cumplimiento Zona:* {emoji_overall} *{compliance:.1f}%*\n"
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
                
            p_emoji = "🟢" if p_compliance >= 95 else "🔴"
            
            # Format according to count-based products
            is_count_based = p_name in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
            if is_count_based:
                msg += f"• 📦 *{p_name}* ({p_emoji} *{p_compliance:.1f}%*)\n"
                msg += f"  ↳ Venta: {round(p_sales):,} / Meta: {round(p_goal):,}\n"
            else:
                msg += f"• 📦 *{p_name}* ({p_emoji} *{p_compliance:.1f}%*)\n"
                msg += f"  ↳ Venta: ${round(p_sales):,} / Meta: ${round(p_goal):,}\n"
                
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
        # Sum of next hour goals for all assigned products
        total_next_hour_goal = 0.0
        for p_name, goal_val in goals_by_product.items():
            total_next_hour_goal += goal_val * next_hour_ratio

        msg = f"📊 *CUMPLIMIENTO DIARIO POR PRODUCTO*\n"
        msg += f"👤 *{user_label}:* {user_name}\n"
        msg += f"📅 *Fecha:* {today_str}\n"
        msg += f"📍 *Zona:* {user_zone}\n"
        msg += f"──────────────────\n"
        msg += f"💰 *Venta Acum. (hasta {ref_hour_str}):* ${round(total_sales_acum):,}\n"
        msg += f"🎯 *Meta Hora Sig. ({next_hour_str}):* ${round(total_next_hour_goal):,}\n"
        msg += f"📈 *Meta del Día:* ${round(total_goals):,}\n"
        msg += f"📊 *Cumplimiento:* {emoji_overall} *{compliance:.1f}%*\n"
        msg += f"──────────────────\n"
        msg += f"📦 *Detalle por Producto:*\n"
        
        all_products = sorted(list(set(list(sales_by_product.keys()) + list(goals_by_product.keys()))))
        for p_name in all_products:
            p_sales_acum = sales_acum_by_product.get(p_name, 0.0)
            p_goal = goals_by_product.get(p_name, 0.0)
            p_sales_total = sales_by_product.get(p_name, 0.0)
            
            if p_goal > 0:
                p_compliance = (p_sales_total / p_goal * 100.0)
            else:
                p_compliance = 100.0 if p_sales_total > 0 else 0.0
                
            p_emoji = "🟢" if p_compliance >= 95 else "🔴"
            p_next_hour_goal = p_goal * next_hour_ratio
            
            is_count_based = p_name in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
            if is_count_based:
                msg += f"• 📦 *{p_name}* ({p_emoji} *{p_compliance:.1f}%*)\n"
                msg += f"  ↳ Acumulado: {round(p_sales_acum):,}\n"
                msg += f"  ↳ Meta Hora Sig: {round(p_next_hour_goal):,}\n"
                msg += f"  ↳ Meta del Día: {round(p_goal):,}\n\n"
            else:
                msg += f"• 📦 *{p_name}* ({p_emoji} *{p_compliance:.1f}%*)\n"
                msg += f"  ↳ Acumulado: ${round(p_sales_acum):,}\n"
                msg += f"  ↳ Meta Hora Sig: ${round(p_next_hour_goal):,}\n"
                msg += f"  ↳ Meta del Día: ${round(p_goal):,}\n\n"
        msg += f"──────────────────\n"
        msg += f"💪 ¡Vamos por la meta! 🚀"
        
    elif report_type == "product_office":
        is_count_based = selected_product in {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
        
        msg = f"📊 *REPORTE PRODUCTO / OFICINA*\n"
        msg += f"👤 *{user_label}:* {user_name}\n"
        msg += f"📅 *Fecha:* {today_str}\n"
        msg += f"📦 *Producto:* *{selected_product}*\n"
        msg += f"──────────────────\n"
        if is_count_based:
            msg += f"💰 *Ventas:* {round(total_sales):,}\n"
            msg += f"🎯 *Meta:* {round(total_goals):,}\n"
        else:
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
            if is_count_based:
                msg += f"• 🏢 *{off_name}* ({emoji_off} *{off_comp:.1f}%*)\n"
                msg += f"  ↳ Venta: {round(off_sales):,} / Meta: {round(off_goal):,}\n"
            else:
                msg += f"• 🏢 *{off_name}* ({emoji_off} *{off_comp:.1f}%*)\n"
                msg += f"  ↳ Venta: ${round(off_sales):,} / Meta: ${round(off_goal):,}\n"
                
        msg += f"──────────────────\n"
        msg += f"💪 ¡Vamos por la meta! 🚀"
        
    else: # report_type == "offices"
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
def get_sitios(force_refresh: bool = Query(False, description="Forzar consulta a Oracle y refrescar catálogo de sitios")):
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
def get_productos(force_refresh: bool = Query(False, description="Forzar consulta a Oracle y refrescar catálogo de productos")):
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

@app.post("/api/upload/metas")
async def upload_metas(files: List[UploadFile] = File(...)):
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
async def upload_distribucion(file: UploadFile = File(...)):
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
def get_metas(fecha: Optional[str] = Query(None, description="Filtrar por fecha YYYY-MM-DD")):
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
def get_metas_products():
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
def toggle_product_goals(data: ToggleProductSchema):
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
def delete_product_goals(product_name: str):
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
def get_distribucion():
    return distribution_store

@app.post("/api/clear")
def clear_data():
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
async def receive_whatsapp_webhook(request: Request):
    """
    Receives incoming WhatsApp messages from Meta, queries the sales cache,
    and replies back using Meta's Cloud API.
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Error parsing Webhook JSON body: {e}")
        return {"status": "error", "message": "Invalid JSON"}
        
    logger.info(f"Received WhatsApp webhook notification: {json.dumps(body)}")
    
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
    
    # 2. Check user role
    promoter = find_active_promoter_by_phone(sender_phone)
    coordinator = None
    if not promoter:
        coordinator = find_active_coordinator_by_phone(sender_phone)
        
    # Check if the user is replying to a prompt (state machine)
    if coordinator:
        # Coordinator Session Routing
        coord_zone = coordinator["zone"]
        zone_promoters = sorted(list(set([
            item.get("promotor") for item in distribution_store 
            if item.get("zona", "").strip().lower() == coord_zone.strip().lower() and item.get("promotor")
        ])))
        
        # 1. Check if coordinator is responding to promoter selection prompt
        if (session_data and isinstance(session_data, dict) and 
            session_data.get("state") == "awaiting_promoter_selection" and 
            message_type == "text" and 
            not any(keyword in user_msg_text.lower() for keyword in ["hola", "menu", "menú", "zona"])):
            
            if user_msg_text.isdigit():
                num = int(user_msg_text)
                if 1 <= num <= len(zone_promoters):
                    selected_promoter = zone_promoters[num - 1]
                    # Save viewing promoter state and keep selected promoter name
                    set_cached_sales(session_key, {"state": "viewing_promoter", "selected_promoter": selected_promoter})
                    query_result = get_whatsapp_query(phone=None, report_type="products", override_promoter_name=selected_promoter)
                else:
                    reply_text = f"❌ Número inválido. Por favor escribe un número entre 1 y {len(zone_promoters)}."
                    query_result = {"text": reply_text, "report_type": "prompt_promoter", "is_coordinator": True}
            else:
                reply_text = f"⚠️ Por favor escribe únicamente el número del promotor (1-{len(zone_promoters)}) o escribe *menu* para cancelar."
                query_result = {"text": reply_text, "report_type": "prompt_promoter", "is_coordinator": True}
                
        # 2. Check if coordinator is responding to product selection prompt for the selected promoter
        elif (session_data and isinstance(session_data, dict) and 
              session_data.get("state") == "awaiting_product_selection" and 
              message_type == "text" and 
              not any(keyword in user_msg_text.lower() for keyword in ["hola", "menu", "menú", "zona", "promotor"])):
            
            current_promoter = session_data.get("selected_promoter")
            if user_msg_text.isdigit():
                num = int(user_msg_text)
                active_products = sorted([p for p, recs in goals_store.items() if recs and recs[0].get("activo", True)])
                if 1 <= num <= len(active_products):
                    selected_product = active_products[num - 1]
                    # Set back to viewing promoter
                    set_cached_sales(session_key, {"state": "viewing_promoter", "selected_promoter": current_promoter})
                    report_type = "product_office"
                    query_result = get_whatsapp_query(phone=None, report_type=report_type, selected_product=selected_product, override_promoter_name=current_promoter)
                else:
                    reply_text = f"❌ Número inválido. Por favor escribe un número entre 1 y {len(active_products)}."
                    query_result = {"text": reply_text}
            else:
                active_products = sorted([p for p, recs in goals_store.items() if recs and recs[0].get("activo", True)])
                reply_text = f"⚠️ Por favor escribe únicamente el número del producto (1-{len(active_products)}) o escribe *menu* para cancelar."
                query_result = {"text": reply_text}
                
        else:
            # Normal routing for coordinator
            report_type = "products" # Default to zone report
            button_id = None
            if message_type == "interactive":
                interactive = message.get("interactive", {})
                button_reply = interactive.get("button_reply", {})
                button_id = button_reply.get("id")
                
            user_msg_lower = user_msg_text.lower()
            
            # If they want to exit to the general zone report
            if (button_id == "view_zone_report" or 
                any(keyword in user_msg_lower for keyword in ["zona", "menu", "menú", "hola"])):
                set_cached_sales(session_key, {"state": "idle"})
                session_data = None
                report_type = "products"
            elif button_id == "view_promoter_by_product" or "promotor" in user_msg_lower:
                report_type = "prompt_promoter"
                set_cached_sales(session_key, {"state": "awaiting_promoter_selection"})
            elif button_id == "view_office_general":
                report_type = "offices"
            elif button_id == "view_prod_office_report":
                report_type = "prompt_product"
                current_promoter = session_data.get("selected_promoter") if (session_data and isinstance(session_data, dict)) else None
                set_cached_sales(session_key, {"state": "awaiting_product_selection", "selected_promoter": current_promoter})
            elif button_id == "view_product_report":
                report_type = "products"
            
            if query_result is None:
                # If they are currently viewing a selected promoter, use their name
                current_promoter = session_data.get("selected_promoter") if (session_data and isinstance(session_data, dict)) else None
                if current_promoter and report_type != "prompt_promoter":
                    query_result = get_whatsapp_query(phone=None, report_type=report_type, selected_product=selected_product, override_promoter_name=current_promoter)
                else:
                    query_result = get_whatsapp_query(sender_phone, report_type=report_type)
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
                    query_result = get_whatsapp_query(sender_phone, report_type=report_type, selected_product=selected_product)
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
                
                if button_id == "view_office_report" or button_id == "view_office_general":
                    report_type = "offices"
                elif button_id == "view_product_report":
                    report_type = "products"
                elif button_id == "view_prod_office_report":
                    report_type = "prompt_product"
                    set_cached_sales(session_key, {"state": "awaiting_product_selection"})
            else:
                user_msg_lower = user_msg_text.lower()
                if "oficina general" in user_msg_lower:
                    set_cached_sales(session_key, {"state": "idle"})
                    report_type = "offices"
                elif "producto / oficina" in user_msg_lower or "producto/oficina" in user_msg_lower:
                    report_type = "prompt_product"
                    set_cached_sales(session_key, {"state": "awaiting_product_selection"})
                elif "oficina" in user_msg_lower:
                    set_cached_sales(session_key, {"state": "idle"})
                    report_type = "offices"
                elif "producto" in user_msg_lower:
                    set_cached_sales(session_key, {"state": "idle"})
                    report_type = "products"
                elif "menu" in user_msg_lower or "menú" in user_msg_lower or "hola" in user_msg_lower:
                    set_cached_sales(session_key, {"state": "idle"})
                    report_type = "products"
                    
            if query_result is None:
                query_result = get_whatsapp_query(sender_phone, report_type=report_type, selected_product=selected_product)
        
    reply_text = query_result.get("text", "❌ Error al procesar consulta.")
    
    # 3. Reply to sender via Meta's Graph API
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    # Retrieve the phone number ID of the bot receiving the message
    phone_number_id = value.get("metadata", {}).get("phone_number_id")
    
    if not whatsapp_token:
        logger.error("WHATSAPP_TOKEN not configured in .env!")
        return {"status": "error", "message": "WHATSAPP_TOKEN not configured"}
        
    if not phone_number_id:
        logger.error("phone_number_id not found in webhook metadata!")
        return {"status": "error", "message": "phone_number_id not found"}
        
    import urllib.request
    import urllib.error
    
    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
    
    # 1. Send the main report as a standard text message (limit 4096 characters, no error 400)
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
    
    if query_result.get("is_coordinator_promoter_view") is True:
        res_report_type = query_result.get("report_type")
        if res_report_type == "products":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_office_general",
                    "title": "Oficina General"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_prod_office_report",
                    "title": "Producto / Oficina"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_zone_report",
                    "title": "Reporte de Zona"
                }
            })
            button_prompt = "📊 Selecciona el tipo de reporte por oficina:"
        elif res_report_type == "offices":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_product_report",
                    "title": "Reporte Productos"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_prod_office_report",
                    "title": "Producto / Oficina"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_zone_report",
                    "title": "Reporte de Zona"
                }
            })
            button_prompt = "📦 Selecciona otra opción para consultar:"
        elif res_report_type == "product_office":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_product_report",
                    "title": "Reporte Productos"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_office_general",
                    "title": "Oficina General"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_zone_report",
                    "title": "Reporte de Zona"
                }
            })
            button_prompt = "📦 Selecciona otra opción para consultar:"
            
    elif query_result.get("is_coordinator") is True:
        res_report_type = query_result.get("report_type")
        if res_report_type == "coordinator_general":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_promoter_by_product",
                    "title": "Promotor por Prod."
                }
            })
            button_prompt = "🔍 ¿Deseas ver el detalle de un promotor específico por producto?"
        elif res_report_type == "prompt_promoter":
            pass
        else:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_zone_report",
                    "title": "Reporte de Zona"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_promoter_by_product",
                    "title": "Otro Promotor"
                }
            })
            button_prompt = "📦 Seleccione una opción:"
            
    elif "promoter" in query_result:
        res_report_type = query_result.get("report_type")
        if res_report_type == "products":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_office_general",
                    "title": "Oficina General"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_prod_office_report",
                    "title": "Producto / Oficina"
                }
            })
            button_prompt = "📊 Selecciona el tipo de reporte por oficina:"
        elif res_report_type == "offices":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_product_report",
                    "title": "Reporte Productos"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_prod_office_report",
                    "title": "Producto / Oficina"
                }
            })
            button_prompt = "📦 Selecciona otra opción para consultar:"
        elif res_report_type == "product_office":
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_product_report",
                    "title": "Reporte Productos"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_office_general",
                    "title": "Oficina General"
                }
            })
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": "view_prod_office_report",
                    "title": "Producto / Oficina"
                }
            })
            button_prompt = "📦 Selecciona otra opción para consultar:"
            
    if buttons:
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

    return {"status": "success", "message": "Reply and menus processed"}


# Serve Frontend Static files
frontend_dir = os.path.join(BASE_DIR, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    logger.warning("Frontend directory not found. API only mode active.")

# Trigger reload comment 2
