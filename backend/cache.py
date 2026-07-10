import os
import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger("cache_module")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")

def init_cache_db():
    """Initializes SQLite database and tables for local sales data caching, whatsapp promoters, and coordinators."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_cache (
                cache_key TEXT PRIMARY KEY,
                data_json TEXT,
                last_updated TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_promoters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                zone TEXT,
                phone TEXT,
                active INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_coordinators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                cedula TEXT,
                role TEXT,
                zone TEXT,
                phone TEXT,
                active INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_administrators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cedula TEXT UNIQUE,
                name TEXT UNIQUE,
                phone TEXT,
                active INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        logger.info("SQLite Cache DB initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing SQLite cache: {e}")
    finally:
        conn.close()

def seed_promoters_from_excel():
    """Seeds the whatsapp_promoters table from Directorio Promotores Excel if empty."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM whatsapp_promoters")
        count = cursor.fetchone()[0]
        if count == 0:
            excel_path = os.path.join(BASE_DIR, "Directorio Promotores Jun 2026 (1).xlsx")
            excel_path = os.path.abspath(excel_path)
            if os.path.exists(excel_path):
                import pandas as pd
                df = pd.read_excel(excel_path)
                df.columns = [str(c).strip() for c in df.columns]
                for idx, row in df.iterrows():
                    name = str(row.get('Promotor', '')).strip()
                    zone = str(row.get('Zona', '')).strip()
                    phone = str(row.get('Celular Corporativo', '')).strip()
                    
                    if name and name.lower() != 'nan':
                        cursor.execute("""
                            INSERT OR IGNORE INTO whatsapp_promoters (name, zone, phone, active)
                            VALUES (?, ?, ?, 1)
                        """, (name, zone, phone))
                conn.commit()
                logger.info(f"Seeded whatsapp_promoters table from {excel_path}")
            else:
                logger.warning(f"Seed file not found at {excel_path}")
    except Exception as e:
        logger.error(f"Error seeding promoters: {e}")
    finally:
        conn.close()

def get_all_promoters():
    """Retrieves all registered promoters sorted by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, zone, phone, active FROM whatsapp_promoters ORDER BY name ASC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting promoters: {e}")
        return []
    finally:
        conn.close()

def add_promoter(name: str, zone: str, phone: str, active: int = 1):
    """Inserts a new promoter, returns the new row ID."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO whatsapp_promoters (name, zone, phone, active)
            VALUES (?, ?, ?, ?)
        """, (name.strip(), zone.strip(), phone.strip(), active))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"El promotor '{name}' ya está registrado.")
    except Exception as e:
        logger.error(f"Error adding promoter: {e}")
        raise e
    finally:
        conn.close()

def update_promoter(pid: int, name: str, zone: str, phone: str, active: int):
    """Updates an existing promoter, returns True if updated."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE whatsapp_promoters
            SET name = ?, zone = ?, phone = ?, active = ?
            WHERE id = ?
        """, (name.strip(), zone.strip(), phone.strip(), active, pid))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        raise ValueError(f"El nombre '{name}' ya está en uso por otro promotor.")
    except Exception as e:
        logger.error(f"Error updating promoter {pid}: {e}")
        raise e
    finally:
        conn.close()

def delete_promoter(pid: int):
    """Deletes a promoter by ID."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM whatsapp_promoters WHERE id = ?", (pid,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting promoter {pid}: {e}")
        return False
    finally:
        conn.close()

def find_active_promoter_by_phone(phone_num: str):
    """Normalize input phone and find an active promoter matching the suffix."""
    clean_digits = "".join(filter(str.isdigit, phone_num))
    if not clean_digits:
        return None
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, zone, phone, active FROM whatsapp_promoters WHERE active = 1")
        rows = cursor.fetchall()
        for r in rows:
            p_clean = "".join(filter(str.isdigit, r["phone"]))
            # Match last 10 digits
            if p_clean and (clean_digits.endswith(p_clean[-10:]) or p_clean.endswith(clean_digits[-10:])):
                return dict(r)
    except Exception as e:
        logger.error(f"Error finding promoter by phone: {e}")
    finally:
        conn.close()
    return None

def get_cached_sales(cache_key: str):
    """Retrieves cached sales records and the timestamp they were last updated."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT data_json, last_updated FROM sales_cache WHERE cache_key = ?", (cache_key,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0]), row[1]
    except Exception as e:
        logger.error(f"Error reading SQLite cache: {e}")
    finally:
        conn.close()
    return None, None

def set_cached_sales(cache_key: str, data: list):
    """Saves or updates sales records in the SQLite cache."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()
        data_json = json.dumps(data)
        cursor.execute("""
            REPLACE INTO sales_cache (cache_key, data_json, last_updated)
            VALUES (?, ?, ?)
        """, (cache_key, data_json, now_str))
        conn.commit()
        logger.info(f"Cached {len(data)} records for key {cache_key}.")
    except Exception as e:
        logger.error(f"Error writing to SQLite cache: {e}")
    finally:
        conn.close()

def clear_cache():
    """Deletes all cached records in the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sales_cache")
        conn.commit()
        logger.info("SQLite cache cleared.")
    except Exception as e:
        logger.error(f"Error clearing SQLite cache: {e}")
    finally:
        conn.close()

def get_daily_session_context(phone: str, user_msg_text: str, button_id: str) -> str:
    """Gestiona la máquina de estados diaria del usuario.
    Retorna 'yesterday' si el usuario está consultando el reporte de ayer (primer contacto del día y flujo subsiguiente),
    o 'today' si está en el flujo normal.
    """
    if not phone:
        return "today"
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_user_requests (
                phone TEXT PRIMARY KEY,
                last_date TEXT,
                session_start_time TEXT,
                date_context TEXT DEFAULT 'today'
            )
        """)
        # Migración: asegurar las columnas en tablas antiguas.
        try:
            cursor.execute("ALTER TABLE whatsapp_user_requests ADD COLUMN session_start_time TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE whatsapp_user_requests ADD COLUMN date_context TEXT DEFAULT 'today'")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        cursor.execute("SELECT last_date, date_context FROM whatsapp_user_requests WHERE phone = ?", (phone,))
        row = cursor.fetchone()

        user_lower = (user_msg_text or "").strip().lower()

        if not row or row[0] != today:
            # Primer mensaje del día: Inicia el estado en 'yesterday'
            cursor.execute(
                "INSERT OR REPLACE INTO whatsapp_user_requests (phone, last_date, session_start_time, date_context) VALUES (?, ?, ?, ?)",
                (phone, today, now.isoformat(), "yesterday")
            )
            conn.commit()
            return "yesterday"

        current_context = row[1] if row[1] else "today"

        # Lógica de transición para salir del ciclo de ayer
        if current_context == "yesterday":
            reset_keywords = ["hola", "menu", "menú", "hoy", "general", "zona", "producto"]
            if any(k == user_lower for k in reset_keywords):
                current_context = "today"
            elif button_id == "view_today_report":
                current_context = "today"

            if current_context == "today":
                cursor.execute("UPDATE whatsapp_user_requests SET date_context = 'today' WHERE phone = ?", (phone,))
                conn.commit()

        return current_context
    except Exception as e:
        logger.error(f"Error in get_daily_session_context: {e}")
        return "today"
    finally:
        conn.close()

def seed_coordinators():
    """Seeds the whatsapp_coordinators table with initial coordinators if empty."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM whatsapp_coordinators")
        count = cursor.fetchone()[0]
        if count == 0:
            initial_coordinators = [
                ("MORALES BURBANO YUDY ANDREA", "25288490", "Coordinador Comercial", "Oriente y municipios Centro", "3207205166"),
                ("HURTADO CAICEDO EDGAR ENRIQUE", "76044229", "Senior Comercial", "Empresa", "3185033565"),
                ("JARAMILLO RUEDA MARIO ANDRES", "94151894", "Coordinador Comercial", "Norte", "3185033572"),
                ("CUERO OBREGON JAMILTON", "1059446686", "Coordinador Comercial", "Occidente", "3207203927"),
                ("ORTIZ CASTILLO SERGIO ALEJANDRO", "1002861726", "Coordinador Comercial", "Sur", "3174238003")
            ]
            for name, cedula, role, zone, phone in initial_coordinators:
                cursor.execute("""
                    INSERT OR IGNORE INTO whatsapp_coordinators (name, cedula, role, zone, phone, active)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (name, cedula, role, zone, phone))
            conn.commit()
            logger.info("Seeded initial coordinators into whatsapp_coordinators table.")
    except Exception as e:
        logger.error(f"Error seeding coordinators: {e}")
    finally:
        conn.close()

def get_all_coordinators():
    """Retrieves all registered coordinators sorted by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, cedula, role, zone, phone, active FROM whatsapp_coordinators ORDER BY name ASC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting coordinators: {e}")
        return []
    finally:
        conn.close()

def add_coordinator(name: str, cedula: str, role: str, zone: str, phone: str, active: int = 1):
    """Inserts a new coordinator, returns the new row ID."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO whatsapp_coordinators (name, cedula, role, zone, phone, active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name.strip(), cedula.strip(), role.strip(), zone.strip(), phone.strip(), active))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"El coordinador '{name}' ya está registrado.")
    except Exception as e:
        logger.error(f"Error adding coordinator: {e}")
        raise e
    finally:
        conn.close()

def update_coordinator(cid: int, name: str, cedula: str, role: str, zone: str, phone: str, active: int):
    """Updates an existing coordinator, returns True if updated."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE whatsapp_coordinators
            SET name = ?, cedula = ?, role = ?, zone = ?, phone = ?, active = ?
            WHERE id = ?
        """, (name.strip(), cedula.strip(), role.strip(), zone.strip(), phone.strip(), active, cid))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        raise ValueError(f"El nombre '{name}' ya está en uso por otro coordinador.")
    except Exception as e:
        logger.error(f"Error updating coordinator {cid}: {e}")
        raise e
    finally:
        conn.close()

def delete_coordinator(cid: int):
    """Deletes a coordinator by ID."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM whatsapp_coordinators WHERE id = ?", (cid,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting coordinator {cid}: {e}")
        return False
    finally:
        conn.close()

def find_active_coordinator_by_phone(phone_num: str):
    """Normalize input phone and find an active coordinator matching the suffix."""
    clean_digits = "".join(filter(str.isdigit, phone_num))
    if not clean_digits:
        return None
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, cedula, role, zone, phone, active FROM whatsapp_coordinators WHERE active = 1")
        rows = cursor.fetchall()
        for r in rows:
            p_clean = "".join(filter(str.isdigit, r["phone"]))
            # Match last 10 digits
            if p_clean and (clean_digits.endswith(p_clean[-10:]) or p_clean.endswith(clean_digits[-10:])):
                return dict(r)
    except Exception as e:
        logger.error(f"Error finding coordinator by phone: {e}")
    finally:
        conn.close()
    return None

def get_all_administrators():
    """Retrieves all registered administrators sorted by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, cedula, phone, active FROM whatsapp_administrators ORDER BY name ASC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting administrators: {e}")
        return []
    finally:
        conn.close()

def add_administrator(name: str, cedula: str, phone: str, active: int = 1):
    """Inserts a new administrator, returns the new row ID."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO whatsapp_administrators (name, cedula, phone, active)
            VALUES (?, ?, ?, ?)
        """, (name.strip(), cedula.strip(), phone.strip(), active))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"El administrador '{name}' o la cédula '{cedula}' ya está registrado.")
    except Exception as e:
        logger.error(f"Error adding administrator: {e}")
        raise e
    finally:
        conn.close()

def update_administrator(aid: int, name: str, cedula: str, phone: str, active: int):
    """Updates an existing administrator, returns True if updated."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE whatsapp_administrators
            SET name = ?, cedula = ?, phone = ?, active = ?
            WHERE id = ?
        """, (name.strip(), cedula.strip(), phone.strip(), active, aid))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        raise ValueError(f"El nombre '{name}' o cédula '{cedula}' ya está en uso por otro administrador.")
    except Exception as e:
        logger.error(f"Error updating administrator {aid}: {e}")
        raise e
    finally:
        conn.close()

def delete_administrator(aid: int):
    """Deletes an administrator by ID."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM whatsapp_administrators WHERE id = ?", (aid,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting administrator {aid}: {e}")
        return False
    finally:
        conn.close()

def find_active_administrator_by_phone(phone_num: str):
    """Normalize input phone and find an active administrator matching the suffix."""
    clean_digits = "".join(filter(str.isdigit, phone_num))
    if not clean_digits:
        return None
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, cedula, phone, active FROM whatsapp_administrators WHERE active = 1")
        rows = cursor.fetchall()
        for r in rows:
            p_clean = "".join(filter(str.isdigit, r["phone"]))
            # Match last 10 digits
            if p_clean and (clean_digits.endswith(p_clean[-10:]) or p_clean.endswith(clean_digits[-10:])):
                return dict(r)
    except Exception as e:
        logger.error(f"Error finding administrator by phone: {e}")
    finally:
        conn.close()
    return None
