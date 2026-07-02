import sqlite3
import json

conn = sqlite3.connect('uploads/cache.db')
cursor = conn.cursor()

cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key LIKE '2026-06-09%'")
row = cursor.fetchone()
if row:
    sales_data = json.loads(row[0])
    
    totals = {"CAUCA": 0.0, "FORTUNA": 0.0}
    for s in sales_data:
        tbl = s.get("Tabla_Origen")
        if tbl == 'SIGT_CHANCES':
            fuente = s.get("Fuente", "UNKNOWN")
            val = float(s.get("Venta_Neta") or 0.0)
            totals[fuente] = totals.get(fuente, 0.0) + val
            
    print("Chance Sales by Source in Local Cache:")
    for src, total in totals.items():
        print(f"  {src}: ${total:,.2f}")
else:
    print("No cache found for today.")

conn.close()
