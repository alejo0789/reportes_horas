import sqlite3
import json

conn = sqlite3.connect('uploads/cache.db')
cursor = conn.cursor()

cursor.execute("SELECT cache_key, last_updated FROM sales_cache WHERE cache_key NOT LIKE 'catalog_%'")
rows = cursor.fetchall()
print("All sales cache entries:")
for r in rows:
    key, updated = r
    # Load and sum Chance
    cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key=?", (key,))
    data = json.loads(cursor.fetchone()[0])
    
    chance_total = 0.0
    for s in data:
        tbl = s.get("Tabla_Origen")
        if tbl == 'SIGT_CHANCES':
            chance_total += float(s.get("Venta_Neta") or 0.0)
            
    print(f"  Key: {key} | Updated: {updated} | Chance Total: ${chance_total:,.2f}")

conn.close()
