import sqlite3
import json

conn = sqlite3.connect('uploads/cache.db')
cursor = conn.cursor()

cursor.execute("SELECT cache_key FROM sales_cache WHERE cache_key LIKE '2026-06-11%'")
rows = cursor.fetchall()
if rows:
    cache_key = rows[0][0]
    cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key=?", (cache_key,))
    data_json = cursor.fetchone()[0]
    sales = json.loads(data_json)
    
    table_counts = {}
    for s in sales:
        t = s.get("Tabla_Origen")
        table_counts[t] = table_counts.get(t, 0) + 1
        
    print("Row counts by Tabla_Origen in cache:")
    for t, count in sorted(table_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count} rows")
else:
    print("No cache found for 2026-06-11")

conn.close()
