import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALES_FILE = os.path.join(BASE_DIR, "scratch", "yesterday_sales.json")
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")

with open(SALES_FILE, "r") as f:
    sales = json.load(f)

# Load catalog_sitios
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_sitios'")
sitios_data = json.loads(cursor.fetchone()[0])
conn.close()

site_to_office = {}
for s in sitios_data:
    s_code = s.get("Cod_Sitio")
    off_code = s.get("Cod_Oficina")
    if s_code is not None:
        site_to_office[int(s_code)] = int(off_code) if off_code is not None else None

rodrigo_offices = {134, 136, 138, 167}

print("--- CHANCE SALES RECORDED AFTER 10:00 PM (22:00:00) ---")
total_after_22 = 0.0
for s in sales:
    if s.get("Tabla_Origen") != 'SIGT_CHANCES':
        continue
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
    site_code = int(site_code)
    
    # Exclude OWO and APP since they are already remapped
    if site_code in [136033, 136034]:
        continue
        
    office_code = site_to_office.get(site_code)
    if office_code in rodrigo_offices:
        hour_str = s.get("Hora", "")
        # Check if hour is >= 22 (10 PM)
        try:
            hour_val = int(hour_str.split(":")[0])
            if hour_val >= 22:
                val = float(s.get("Venta_Neta") or 0.0)
                total_after_22 += val
                print(f"Time: {hour_str} | Site: {site_code} | Office: {office_code} | Venta: ${val:,.2f}")
        except ValueError:
            pass

print(f"\nTotal CHANCE sales after 10:00 PM: ${total_after_22:,.2f}")
