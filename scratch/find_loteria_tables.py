import sys
import os
sys.path.insert(0, os.getcwd())

from backend.db import db_manager
import logging

logging.basicConfig(level=logging.INFO)
db_manager.init_pools()

query = """
SELECT table_name
FROM all_tables
WHERE table_name LIKE '%LOTERIA%'
"""

print("\n--- CAUCAMED ---")
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                for row in cursor.fetchall():
                    print(row[0])
    except Exception as e:
        print(f"CAUCAMED query failed: {e}")

db_manager.close_pools()
