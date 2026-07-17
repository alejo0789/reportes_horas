import sys
import os
sys.path.insert(0, os.getcwd())

from backend.db import db_manager
import logging

logging.basicConfig(level=logging.INFO)
db_manager.init_pools()

desde = "2026-06-24 00:00:00"
hasta = "2026-06-25 00:00:00"

query = """
SELECT SUM(NVL(vlr_pagado, 0)) as venta 
FROM GANA_SIGA.SIGT_LOTERIAS
WHERE fec_venta >= TO_DATE(:desde, 'YYYY-MM-DD HH24:MI:SS')
  AND fec_venta < TO_DATE(:hasta, 'YYYY-MM-DD HH24:MI:SS')
"""

print("\n--- CAUCAMED SIGT_LOTERIAS ---")
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, {"desde": desde, "hasta": hasta})
                print(cursor.fetchone())
    except Exception as e:
        print(f"CAUCAMED query failed: {e}")

db_manager.close_pools()
