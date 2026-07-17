import sys
import os
sys.path.insert(0, os.getcwd())

from backend.db import db_manager
from backend.queries import VENTAS_POR_HORA_QUERY
import logging

logging.basicConfig(level=logging.INFO)
db_manager.init_pools()

desde = "2026-06-24 00:00:00"
hasta = "2026-06-25 00:00:00"

results = []
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    if row_dict["Tabla_Origen"] == 'SIGT_LOTERIAS_LINEA':
                        results.append(row_dict)
    except Exception as e:
        print(f"CAUCAMED query failed: {e}")

total = sum(r["Venta_Neta"] for r in results)
print(f"Total SIGT_LOTERIAS_LINEA in VENTAS_POR_HORA_QUERY: {total}")

db_manager.close_pools()
