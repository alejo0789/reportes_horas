import sys
import os
sys.path.insert(0, os.getcwd())

from backend.db import db_manager
import logging

logging.basicConfig(level=logging.INFO)
db_manager.init_pools()

query = """
SELECT
    t.ide_estado,
    COUNT(*) as num_transacciones
FROM GANA_SIGA.SIGT_LOTERIAS_LINEA t
WHERE t.fec_venta >= TO_DATE('2026-06-01', 'YYYY-MM-DD')
GROUP BY t.ide_estado
"""

print("\n--- CAUCAMED SIGT_LOTERIAS_LINEA STATES FOR JUNE ---")
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    print(row_dict)
    except Exception as e:
        print(f"CAUCAMED query failed: {e}")

db_manager.close_pools()
