import sqlite3
import json

conn = sqlite3.connect('uploads/cache.db')
cursor = conn.cursor()

cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key='catalog_productos'")
row = cursor.fetchone()
if row:
    products = json.loads(row[0])
    for p in products:
        name = str(p.get("Producto", "")).upper()
        tipo = str(p.get("Tipo_Producto", p.get("Tipo Producto", ""))).upper()
        if "GIRO" in name or "GIRO" in tipo:
            print(f"ID: {p.get('Cod_Producto')}, Name: {p.get('Producto')}, Type: {p.get('Tipo_Producto', p.get('Tipo Producto'))}")
else:
    print("Catalog not found.")

conn.close()
