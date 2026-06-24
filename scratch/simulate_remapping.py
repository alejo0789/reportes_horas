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

# ORIGINAL RODRIGO CHANCE SALES
orig_rodrigo_chance = 0.0
for s in sales:
    if s.get("Tabla_Origen") != 'SIGT_CHANCES':
        continue
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
    site_code = int(site_code)
    office_code = site_to_office.get(site_code)
    if office_code in rodrigo_offices:
        orig_rodrigo_chance += float(s.get("Venta_Neta") or 0.0)

print(f"Original Rodrigo CHANCE sales: ${orig_rodrigo_chance:,.2f}")

# SIMULATED RODRIGO CHANCE SALES (with 136033 -> 333 and 136034 -> 334)
sim_rodrigo_chance = 0.0
for s in sales:
    if s.get("Tabla_Origen") != 'SIGT_CHANCES':
        continue
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
    site_code = int(site_code)
    
    # REMAP
    office_code = site_to_office.get(site_code)
    if site_code == 136033:
        office_code = 333
    elif site_code == 136034:
        office_code = 334
        
    if office_code in rodrigo_offices:
        sim_rodrigo_chance += float(s.get("Venta_Neta") or 0.0)

print(f"Simulated Rodrigo CHANCE sales: ${sim_rodrigo_chance:,.2f}")
print(f"Difference: ${orig_rodrigo_chance - sim_rodrigo_chance:,.2f}")
print(f"Target yesterday: $6,287,850.00 | Simulated: ${sim_rodrigo_chance:,.2f}")
print(f"Simulated vs Target gap: ${sim_rodrigo_chance - 6287850:,.2f}")
