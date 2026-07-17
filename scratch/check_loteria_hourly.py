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

query = """
SELECT
    TO_CHAR(TRUNC(t.fec_venta, 'HH24'), 'HH24:MI:SS') as hora,
    SUM(NVL(t.vlr_pagado, 0)) AS total_venta_neta
FROM GANA_SIGA.SIGT_LOTERIAS_LINEA t
WHERE t.fec_venta >= TO_DATE(:desde, 'YYYY-MM-DD HH24:MI:SS')
  AND t.fec_venta < TO_DATE(:hasta, 'YYYY-MM-DD HH24:MI:SS')
  AND t.ide_estado IN (3)
GROUP BY TO_CHAR(TRUNC(t.fec_venta, 'HH24'), 'HH24:MI:SS')
ORDER BY hora
"""

print("\n--- CAUCAMED SIGT_LOTERIAS_LINEA by Hour ---")
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, {"desde": desde, "hasta": hasta})
                for row in cursor.fetchall():
                    print(row)
    except Exception as e:
        print(f"CAUCAMED query failed: {e}")

db_manager.close_pools()
