import sqlite3
import json
import os

db_path = "uploads/cache.db"
if not os.path.exists(db_path):
    print("uploads/cache.db not found")
    sys.exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key='catalog_productos'")
cat_row = cursor.fetchone()
if cat_row:
    products = json.loads(cat_row[0])
    print("--- Product Catalog ---")
    for p in sorted(products, key=lambda x: int(x.get("Cod. Producto") or x.get("Cod_Producto") or 0)):
        cod = p.get("Cod. Producto") or p.get("Cod_Producto")
        name = p.get("Producto")
        ptype = p.get("Tipo_Producto") or p.get("Tipo Producto")
        print(f"  Code {cod:<5} | Name: {name:<35} | Type: {ptype}")
else:
    print("Catalog not found")

conn.close()
