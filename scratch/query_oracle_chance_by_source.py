import sys
import os
sys.path.insert(0, os.getcwd())

from backend.db import db_manager
from backend.queries import VENTAS_POR_HORA_QUERY
import logging

logging.basicConfig(level=logging.INFO)
db_manager.init_pools()

desde = "2026-06-09 00:00:00"
hasta = "2026-06-09 23:59:59"

cauca_chance = 0.0
fortuna_chance = 0.0

if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    if row_dict.get("Tabla_Origen") == "SIGT_CHANCES":
                        cauca_chance += float(row_dict.get("Venta_Neta") or 0.0)
    except Exception as e:
        print(f"CAUCAMED query failed: {e}")

if db_manager.pool_fortuna:
    try:
        with db_manager.get_fortuna_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    if row_dict.get("Tabla_Origen") == "SIGT_CHANCES":
                        fortuna_chance += float(row_dict.get("Venta_Neta") or 0.0)
    except Exception as e:
        print(f"FORTUMED query failed: {e}")

print(f"\nFresh Oracle Chance sales:")
print(f"  CAUCA: ${cauca_chance:,.2f}")
print(f"  FORTUNA: ${fortuna_chance:,.2f}")
print(f"  TOTAL: ${cauca_chance + fortuna_chance:,.2f}")

db_manager.close_pools()
