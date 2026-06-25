import sqlite3
import json

c = sqlite3.connect('uploads/cache.db').cursor()
c.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_productos'")
r = c.fetchone()
prods = json.loads(r[0]) if r else []

for p in prods:
    if "BALOTO" in str(p.get("Producto", "")).upper() or "BALOTO" in str(p.get("Tipo_Producto", "")).upper() or "BALOTO" in str(p.get("Tipo Producto", "")).upper():
        print(p)
