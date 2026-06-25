import sqlite3
import json

c = sqlite3.connect('uploads/cache.db').cursor()
c.execute("SELECT data_json FROM sales_cache WHERE cache_key = '2026-06-24 00:00:00_2026-06-24 23:59:59'")
row = c.fetchone()
sales_list = json.loads(row[0]) if row else []

baloto_sales = [s for s in sales_list if str(s.get("Cod_Producto")) == "22059" or s.get("Cod_Producto") == 22059]
print("Records with Cod_Producto = 22059:", len(baloto_sales))
total = sum(s.get("Venta_Neta", 0) for s in baloto_sales)
print("Total Venta_Neta para 22059:", total)

all_codes = set(s.get("Cod_Producto") for s in sales_list)
print("Some codes:", list(all_codes)[:20])
