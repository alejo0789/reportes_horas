import sqlite3
import json
import os

DB_PATH = "uploads/cache.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check keys
cursor.execute("SELECT cache_key, last_updated FROM sales_cache")
keys = cursor.fetchall()
print("Keys in cache:")
for k in keys:
    print(k)

cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key LIKE '2026-06-24%'")
row = cursor.fetchone()

if row:
    data = json.loads(row[0])
    print(f"\nFound {len(data)} rows for 2026-06-24 in cache.")
    total = sum(float(item.get("Venta_Neta", 0) or 0) for item in data if item.get("Tabla_Origen") not in ('SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'))
    print(f"Total Venta_Neta in cache: {total}")
    
    # Calculate total for LOTERIA
    total_loteria = sum(float(item.get("Venta_Neta", 0) or 0) for item in data if item.get("Tabla_Origen") == 'SIGT_LOTERIAS_LINEA')
    print(f"Total LOTERIA in cache: {total_loteria}")

conn.close()
