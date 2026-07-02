import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")
SALES_FILE = os.path.join(BASE_DIR, "scratch", "yesterday_sales.json")

with open(SALES_FILE, "r") as f:
    sales = json.load(f)

# Load catalog_sitios from cache.db
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
    site_name = s.get("Sitio_Venta")
    if s_code is not None:
        site_to_office[int(s_code)] = int(off_code) if off_code is not None else None
        site_to_name[int(s_code)] = site_name

rodrigo_offices = {134, 136, 138, 167}

# Get all Chance sales for Rodrigo yesterday
chance_sales = []
for s in sales:
    if s.get("Tabla_Origen") != 'SIGT_CHANCES':
        continue
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
    site_code = int(site_code)
    office_code = site_to_office.get(site_code)
    if office_code in rodrigo_offices:
        chance_sales.append(s)

# Look for transactions that equal 14000
for s in chance_sales:
    val = float(s.get("Venta_Neta") or 0.0)
    if val == 14000.0:
        print("Found 14000 transaction:", s, "Site Name:", site_to_name.get(int(s["Cod_Sitio"])))

# Let's search for combinations or any other details
# Let's print all transaction values for sites 136033 and 136034 and check if any other site has OWO-like values
print("\nChecking for any other transactions with decimal parts on other sites:")
for s in chance_sales:
    val = float(s.get("Venta_Neta") or 0.0)
    site_code = int(s["Cod_Sitio"])
    if site_code not in [136033, 136034] and val % 1 != 0:
        print(f"Decimal sale on Site {site_code} ({site_to_name.get(site_code)}): ${val} | Record: {s}")
