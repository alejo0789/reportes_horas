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
                    if row_dict["Hora"].startswith('20:'):
                        results.append(row_dict)
    except Exception as e:
        print(f"CAUCAMED query failed: {e}")

totals_at_20 = {}
for r in results:
    src_table = r["Tabla_Origen"]
    val = float(r["Venta_Neta"] or 0)
    totals_at_20[src_table] = totals_at_20.get(src_table, 0) + val

print("\n--- CAUCAMED TOTALS AT 20:00 ---")
for t, v in totals_at_20.items():
    print(f"{t}: {v}")

db_manager.close_pools()
