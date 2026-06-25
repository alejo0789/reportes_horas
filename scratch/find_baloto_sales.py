import sqlite3
import json

c = sqlite3.connect('uploads/cache.db').cursor()
c.execute("SELECT data_json FROM sales_cache WHERE cache_key = '2026-06-24 00:00:00_2026-06-24 23:59:59'")
row = c.fetchone()
sales_list = json.loads(row[0]) if row else []

sums = {}
for s in sales_list:
    cod = s.get("Cod_Producto")
    v = float(s.get("Venta_Neta") or 0.0)
    sums[cod] = sums.get(cod, 0.0) + v

print("Sales by Cod_Producto:")
for cod, v in sums.items():
    print(f"Cod {cod}: {v}")
