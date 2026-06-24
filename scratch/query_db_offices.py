import os
from dotenv import load_dotenv
load_dotenv()

from backend.db import db_manager

db_manager.init_pools()

query = """
SELECT 
    SV.IDE_SITIOVENTA, SV.NOM_SITIOVENTA, SV.IDE_OFICINA, SV.ACTIVO 
FROM 
    GANA_MAESTROS.MAET_SITIOSVENTA SV 
WHERE 
    SV.IDE_OFICINA IN (333, 334)
"""

print("Querying master sites for offices 333 and 334 on CAUCAMED...")
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                print(f"Found {len(rows)} sites in CAUCAMED:")
                for r in rows:
                    print(r)
    except Exception as e:
        print("Error on CAUCAMED:", e)

print("\nQuerying master sites for offices 333 and 334 on FORTUMED...")
if db_manager.pool_fortuna:
    try:
        with db_manager.get_fortuna_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                print(f"Found {len(rows)} sites in FORTUMED:")
                for r in rows:
                    print(r)
    except Exception as e:
        print("Error on FORTUMED:", e)

db_manager.close_pools()
