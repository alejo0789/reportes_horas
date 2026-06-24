import json
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")
SALES_FILE = os.path.join(BASE_DIR, "scratch", "yesterday_sales.json")

with open(SALES_FILE, "r") as f:
    sales = json.load(f)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_sitios'")
sitios_data = json.loads(cursor.fetchone()[0])
conn.close()

site_to_office = {}
site_to_name = {}
for s in sitios_data:
    s_code = s.get("Cod_Sitio")
    off_code = s.get("Cod_Oficina")
    off_name = s.get("Oficina")
    site_name = s.get("Sitio_Venta")
    if s_code is not None:
        site_to_office[int(s_code)] = int(off_code) if off_code is not None else None
        site_to_name[int(s_code)] = site_name

rodrigo_offices = {134, 136, 138, 167}

# Filter yesterday's sales for Rodrigo's offices and CHANCE
chance_sales = []
for s in sales:
    # Chance table
    if s.get("Tabla_Origen") != 'SIGT_CHANCES':
        continue
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
    site_code = int(site_code)
    office_code = site_to_office.get(site_code)
    if office_code in rodrigo_offices:
        chance_sales.append(s)

print(f"Total Chance sales records: {len(chance_sales)}")

# Group by site
sales_by_site = {}
for s in chance_sales:
    site_code = int(s["Cod_Sitio"])
    office_code = site_to_office.get(site_code)
    site_name = site_to_name.get(site_code, f"Sitio {site_code}")
    val = float(s.get("Venta_Neta") or 0.0)
    
    if site_code not in sales_by_site:
        sales_by_site[site_code] = {
            "site_code": site_code,
            "site_name": site_name,
            "office_code": office_code,
            "venta": 0.0
        }
    sales_by_site[site_code]["venta"] += val

print("\n--- CHANCE SALES BY SITE FOR RODRIGO ---")
for s in sorted(sales_by_site.values(), key=lambda x: x["venta"], reverse=True):
    print(f"Site {s['site_code']} ({s['site_name']}) in Office {s['office_code']}: ${s['venta']:,.2f}")
