import sys
import os
sys.path.insert(0, os.getcwd())

from backend.db import db_manager
import logging

logging.basicConfig(level=logging.INFO)
db_manager.init_pools()

query = """
SELECT column_name, data_type 
FROM all_tab_columns 
WHERE table_name = 'SIGT_LOTERIAS_LINEA'
"""

print("\n--- CAUCAMED SIGT_LOTERIAS_LINEA Columns ---")
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                for row in cursor.fetchall():
                    print(row)
    except Exception as e:
        print(f"CAUCAMED query failed: {e}")

db_manager.close_pools()
