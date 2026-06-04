import os
import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger("cache_module")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")

def init_cache_db():
    """Initializes SQLite database and tables for local sales data caching and whatsapp promoters."""
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
