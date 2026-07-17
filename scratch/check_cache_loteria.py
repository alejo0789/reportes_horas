import json
import sqlite3
import sys

conn = sqlite3.connect('uploads/cache.db')
cursor = conn.cursor()

cursor.execute("SELECT cache_key FROM sales_cache WHERE cache_key LIKE '2026-06-24%'")
keys = cursor.fetchall()
if keys:
    key = keys[0][0]
    cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key=?", (key,))
    sales_data = json.loads(cursor.fetchone()[0])
    
    total_loteria = 0
    for s in sales_data:
        src_table = s.get("Tabla_Origen")
        if src_table == 'SIGT_LOTERIAS_LINEA':
            total_loteria += float(s.get("Venta_Neta") or 0.0)
            
    print(f"Total Loteria in cache {key}: {total_loteria}")
else:
    print("No cache found for 2026-06-24.")

conn.close()
