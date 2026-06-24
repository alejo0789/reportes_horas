import os
import sys
import json
from datetime import datetime

# Set PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import db_manager
from backend.queries import VENTAS_POR_HORA_QUERY
from backend.main import rows_to_dicts

# Initialize connection pools
db_manager.init_pools()

desde = "2026-06-17 00:00:00"
hasta = "2026-06-17 23:59:59"

print("Querying Oracle CAUCAMED...")
cauca_sales = []
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                cauca_sales = rows_to_dicts(cursor)
                print(f"Retrieved {len(cauca_sales)} sales from CAUCAMED.")
    except Exception as e:
        print(f"Error querying CAUCAMED: {e}")
else:
    print("CAUCAMED pool not initialized.")

print("Querying Oracle FORTUMED...")
fortuna_sales = []
if db_manager.pool_fortuna:
    try:
        with db_manager.get_fortuna_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                fortuna_sales = rows_to_dicts(cursor)
                print(f"Retrieved {len(fortuna_sales)} sales from FORTUMED.")
    except Exception as e:
        print(f"Error querying FORTUMED: {e}")
else:
    print("FORTUMED pool not initialized.")

# Load site to office catalog from database to be 100% accurate
import sqlite3
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

# Rodrigo's offices
rodrigo_offices = {134, 136, 138, 167}
excluded_sites = {136033, 136034}

print("\n--- ANALYZING DIRECT CHANCE SALES FROM ORACLE ---")
print("Office | Site Code | Site Name | Net Chance Sales")
print("-" * 75)

totals_by_office = {off: 0.0 for off in rodrigo_offices}
totals_by_site = {}

# Combine results from both databases
all_sales = cauca_sales + fortuna_sales

for s in all_sales:
    if s.get("Tabla_Origen") != 'SIGT_CHANCES':
        continue
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
    site_code = int(site_code)
    
    # Skip excluded sites
    if site_code in excluded_sites:
        continue
        
    office_code = site_to_office.get(site_code)
    if office_code in rodrigo_offices:
        val = float(s.get("Venta_Neta") or 0.0)
        totals_by_office[office_code] += val
        totals_by_site[site_code] = totals_by_site.get(site_code, 0.0) + val

grand_total = 0.0
for office in sorted(rodrigo_offices):
    print(f"\nOffice: {office}")
    office_total = 0.0
    for scode in sorted(totals_by_site.keys()):
        if site_to_office.get(scode) == office:
            sval = totals_by_site[scode]
            office_total += sval
            sname = site_to_name.get(scode, "Unknown")
            print(f"       | {scode:<9} | {sname:<35} | ${sval:,.2f}")
    print(f"Office {office} Total: ${office_total:,.2f}")
    grand_total += office_total

print("\n" + "=" * 75)
print(f"GRAND TOTAL CHANCE SALES (EXCLUDING OWO/APP): ${grand_total:,.2f}")
print("=" * 75)
