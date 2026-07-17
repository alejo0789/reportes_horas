import sys
import os
sys.path.insert(0, os.getcwd())

from backend.db import db_manager
import logging

logging.basicConfig(level=logging.INFO)
db_manager.init_pools()

desde = "2026-06-24 00:00:00"
hasta = "2026-06-24 23:59:59"

query = """
SELECT
    t.es_venta_reserva,
    t.es_venta_fisica,
    SUM(NVL(t.vlr_pagado, 0)) AS total_venta_neta,
    COUNT(*) as num_transacciones
FROM GANA_SIGA.SIGT_LOTERIAS_LINEA t
WHERE t.fec_venta >= TO_DATE(:desde, 'YYYY-MM-DD HH24:MI:SS')
  AND t.fec_venta <= TO_DATE(:hasta, 'YYYY-MM-DD HH24:MI:SS')
GROUP BY t.es_venta_reserva, t.es_venta_fisica
"""

print("\n--- CAUCAMED SIGT_LOTERIAS_LINEA ---")
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, {"desde": desde, "hasta": hasta})
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    print(row_dict)
    except Exception as e:
        print(f"CAUCAMED query failed: {e}")

db_manager.close_pools()
