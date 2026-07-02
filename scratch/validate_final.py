import json
import os
import sqlite3
from datetime import datetime
import sys

# Ensure stdout uses UTF-8 to prevent encoding crashes with emojis
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.main import get_ventas, get_whatsapp_query, goals_store, distribution_store
from backend.cache import init_cache_db, seed_promoters_from_excel, seed_coordinators, set_cached_sales

init_cache_db()
seed_promoters_from_excel()
seed_coordinators()

# Seed cache database with actual yesterday sales from yesterday_sales.json
SALES_FILE = os.path.join(BASE_DIR, "scratch", "yesterday_sales.json")
with open(SALES_FILE, "r") as f:
    actual_sales = json.load(f)

desde = "2026-06-17 00:00:00"
hasta = "2026-06-17 23:59:59"
cache_key = f"{desde}_{hasta}"

# Write it directly using cache system
set_cached_sales(cache_key, actual_sales)
print(f"Seeded SQLite cache key '{cache_key}' with {len(actual_sales)} records.")

print("\n--- TESTING GET_VENTAS ---")
resp = get_ventas(desde=desde, hasta=hasta, force_refresh=False)
sales = resp["data"]
print(f"Total sales records returned: {len(sales)}")

# Load site to office map from catalog_sitios
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")
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

# Add normalized app sites manually
site_to_office[333033] = 333
site_to_office[334034] = 334
site_to_name[333033] = "Ventas OWO"
site_to_name[334034] = "Ventas APP Su Red"

rodrigo_offices = {134, 136, 138, 167}

rodrigo_chance_sales = 0.0
rodrigo_site_totals = {}

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
        rodrigo_chance_sales += val
        rodrigo_site_totals[site_code] = rodrigo_site_totals.get(site_code, 0.0) + val

print(f"\nRodrigo Ledezma CHANCE sales yesterday: ${rodrigo_chance_sales:,.2f}")
print("Expected CHANCE sales: $6,287,850.00")

if abs(rodrigo_chance_sales - 6287850.0) < 0.01:
    print("SUCCESS: Rodrigo's Chance sales match exactly!")
else:
    print(f"FAILURE: Discrepancy detected! Diff: {rodrigo_chance_sales - 6287850.0}")

# Print sales for the app offices 333 and 334 to ensure they are captured correctly
owo_chance_sales = sum(float(s.get("Venta_Neta") or 0.0) for s in sales if s.get("Tabla_Origen") == 'SIGT_CHANCES' and site_to_office.get(int(s.get("Cod_Sitio"))) == 333)
app_chance_sales = sum(float(s.get("Venta_Neta") or 0.0) for s in sales if s.get("Tabla_Origen") == 'SIGT_CHANCES' and site_to_office.get(int(s.get("Cod_Sitio"))) == 334)

print(f"\nOffice 333 (OWO) CHANCE sales yesterday: ${owo_chance_sales:,.2f}")
print(f"Office 334 (APP) CHANCE sales yesterday: ${app_chance_sales:,.2f}")

print("\n--- TESTING WHATSAPP BOT QUERY FOR RODRIGO ---")
from backend.cache import get_all_promoters
promoters = get_all_promoters()
rodrigo = next((p for p in promoters if "rodrigo" in p["name"].lower()), None)

if rodrigo:
    print(f"Found Rodrigo promoter record: {rodrigo}")
    # Mock datetime.now() in get_whatsapp_query if needed, but since we query by today's date in get_whatsapp_query:
    # Wait! get_whatsapp_query queries today's sales.
    # To test get_whatsapp_query on yesterday's sales, we can temporarily seed today's cache key with the same data!
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_key = f"{today_str} 00:00:00_{today_str} 23:59:59"
    set_cached_sales(today_key, actual_sales)
    print(f"Seeded today's SQLite cache key '{today_key}' to mock WhatsApp query report.")
    
    query_resp = get_whatsapp_query(phone=rodrigo["phone"], report_type="products")
    print("\nWhatsApp query output for Rodrigo:")
    print(query_resp.get("text"))
else:
    print("Rodrigo not found in registered WhatsApp promoters.")
