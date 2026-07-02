import os
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from backend.db import db_manager
from backend.queries import VENTAS_POR_HORA_QUERY

# Init database manager pools
db_manager.init_pools()

# Let's query yesterday: 2026-06-17
desde = "2026-06-17 00:00:00"
hasta = "2026-06-17 23:59:59"

print(f"Querying databases for range {desde} to {hasta}...")

results = []

def rows_to_dicts(cursor):
    columns = [col[0] for col in cursor.description]
    results = []
    for row in cursor.fetchall():
        row_dict = {}
        for col_name, val in zip(columns, row):
            if isinstance(val, datetime):
                row_dict[col_name] = val.isoformat()
            else:
                row_dict[col_name] = val
            results.append(row_dict)
    return results

# Query CAUCAMED
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                cauca_res = []
                columns = [col[0] for col in cursor.description]
                for r in cursor.fetchall():
                    row_dict = dict(zip(columns, r))
                    row_dict["Fuente"] = "CAUCA"
                    cauca_res.append(row_dict)
                results.extend(cauca_res)
                print(f"Retrieved {len(cauca_res)} rows from CAUCAMED.")
    except Exception as e:
        print(f"CAUCAMED failed: {e}")
else:
    print("CAUCAMED pool not initialized.")

# Query FORTUMED
if db_manager.pool_fortuna:
    try:
        with db_manager.get_fortuna_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                fortuna_res = []
                columns = [col[0] for col in cursor.description]
                for r in cursor.fetchall():
                    row_dict = dict(zip(columns, r))
                    row_dict["Fuente"] = "FORTUNA"
                    fortuna_res.append(row_dict)
                results.extend(fortuna_res)
                print(f"Retrieved {len(fortuna_res)} rows from FORTUMED.")
    except Exception as e:
        print(f"FORTUMED failed: {e}")
else:
    print("FORTUMED pool not initialized.")

# Save results to scratch/yesterday_sales.json for quick access
with open("scratch/yesterday_sales.json", "w") as f:
    json.dump(results, f, default=str, indent=2)

print(f"Total sales records retrieved: {len(results)}")

# Close pools
db_manager.close_pools()
