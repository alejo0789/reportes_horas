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

# 1. Collect app site users
app_site_users = set()
for s in sales:
    site_code = s.get("Cod_Sitio")
    if site_code is not None and int(site_code) in [136033, 136034]:
        user = s.get("Ide_Usuario") or s.get("IDE_USUARIO")
        if user is not None:
            app_site_users.add(user)

print("User IDs on app sites 136033/136034:", app_site_users)

# 2. Check all Chance sales under Rodrigo's offices, grouped by User and Site
user_site_sales = {}
for s in sales:
    if s.get("Tabla_Origen") != 'SIGT_CHANCES':
        continue
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
    site_code = int(site_code)
    office_code = site_to_office.get(site_code)
    if office_code in rodrigo_offices:
        user = s.get("Ide_Usuario") or s.get("IDE_USUARIO")
        val = float(s.get("Venta_Neta") or 0.0)
        key = (user, site_code)
        user_site_sales[key] = user_site_sales.get(key, 0.0) + val

print("\n--- CHANCE SALES BY USER AND SITE IN RODRIGO'S OFFICES ---")
for (user, site), total in sorted(user_site_sales.items(), key=lambda x: x[1], reverse=True):
    s_name = site_to_name.get(site, f"Sitio {site}")
    is_app_user = "YES" if user in app_site_users else "NO"
    print(f"User: {user:<8} | App User: {is_app_user} | Site: {site:<8} ({s_name:<35}) | Office: {site_to_office.get(site)} | Total: ${total:,.2f}")
