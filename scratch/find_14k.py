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
    site_name = s.get("Sitio_Venta")
    if s_code is not None:
        site_to_office[int(s_code)] = int(off_code) if off_code is not None else None
        site_to_name[int(s_code)] = site_name

rodrigo_offices = {134, 136, 138, 167}

# Let's inspect all sites under Rodrigo's offices and check their names and chance totals
chance_by_site = {}
for s in sales:
    if s.get("Tabla_Origen") != 'SIGT_CHANCES':
        continue
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
    site_code = int(site_code)
    office_code = site_to_office.get(site_code)
    
    if office_code in rodrigo_offices:
        val = float(s.get("Venta_Neta") or 0.0)
        if site_code not in chance_by_site:
            chance_by_site[site_code] = {
                "code": site_code,
                "name": site_to_name.get(site_code, f"Sitio {site_code}"),
                "office": office_code,
                "total": 0.0,
                "tx_count": 0
            }
        chance_by_site[site_code]["total"] += val
        chance_by_site[site_code]["tx_count"] += 1

print("Sites under Rodrigo's offices with Chance sales:")
for s in sorted(chance_by_site.values(), key=lambda x: x["total"]):
    print(f"Office {s['office']} | Code: {s['code']} | Name: {s['name']} | Total: ${s['total']:,.2f} | Count: {s['tx_count']}")
