import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALES_FILE = os.path.join(BASE_DIR, "scratch", "yesterday_sales.json")

with open(SALES_FILE, "r") as f:
    sales = json.load(f)

# Filter for the OWO and APP sites (both original and remapped codes)
app_site_codes = {136033, 136034, 333033, 334034}

print("--- ALL SALES FOR OWO / APP SITES BY PRODUCT ---")
app_sales_by_product = {}
for s in sales:
    site_code = s.get("Cod_Sitio")
    if site_code is not None and int(site_code) in app_site_codes:
        prod_code = s.get("Cod_Producto")
        src_table = s.get("Tabla_Origen")
        key = f"Prod: {prod_code} | Table: {src_table}"
        val = float(s.get("Venta_Neta") or 0.0)
        app_sales_by_product[key] = app_sales_by_product.get(key, 0.0) + val

for k, v in app_sales_by_product.items():
    print(f"{k}: ${v:,.2f}")
