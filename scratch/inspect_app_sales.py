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

# Let's find all sites that might be app-related
app_sites = []
for s in sitios_data:
    name = str(s.get("Sitio_Venta", "")).upper()
    code = s.get("Cod_Sitio")
    off = s.get("Cod_Oficina")
    if "OWO" in name or "APP" in name or "APLICATIVO" in name or "SU RED" in name or "SURED" in name:
        app_sites.append(s)

print("--- APP-RELATED SITES IN CATALOGUE ---")
for s in app_sites:
    print(f"Code: {s['Cod_Sitio']} | Name: {s['Sitio_Venta']} | Office: {s['Cod_Oficina']}")

# Now let's calculate sales yesterday for these specific sites
print("\n--- YESTERDAY'S SALES FOR THESE SITES ---")
app_site_codes = [s["Cod_Sitio"] for s in app_sites]

# Also let's check sales for 136033 and 136034 specifically
target_codes = {136033, 136034}
for c in app_site_codes:
    target_codes.add(int(c))

sales_by_app_site = {}
for s in sales:
    src_table = s.get("Tabla_Origen")
    if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
        continue
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
    site_code = int(site_code)
    
    if site_code in target_codes:
        val = float(s.get("Venta_Neta") or 0.0)
        prod = s.get("Cod_Producto") # Let's print product code or table origin
        # Resolve product name
        # We can just print the raw record info
        if site_code not in sales_by_app_site:
            sales_by_app_site[site_code] = []
        sales_by_app_site[site_code].append(s)

total_chance_app = 0.0
for code, records in sorted(sales_by_app_site.items()):
    # Find site name
    s_name = next((s["Sitio_Venta"] for s in sitios_data if s["Cod_Sitio"] == code), f"Sitio {code}")
    print(f"\nSite {code} ({s_name}):")
    site_total = 0.0
    for r in records:
        val = float(r.get("Venta_Neta") or 0.0)
        site_total += val
        # Let's normalize name
        # If it is chance
        if r.get("Tabla_Origen") == 'SIGT_CHANCES':
            total_chance_app += val
            print(f"  CHANCE: ${val:,.2f}")
        else:
            print(f"  {r.get('Tabla_Origen')} (Prod {r.get('Cod_Producto')}): ${val:,.2f}")
    print(f"  Total: ${site_total:,.2f}")

print(f"\nTotal CHANCE sales across all detected APP sites: ${total_chance_app:,.2f}")

# Let's see: Rodrigo's total chance sales yesterday was 6,673,043.15.
# If we subtract total_chance_app from Rodrigo's CHANCE sales, what do we get?
# Rodrigo's CHANCE was $6,673,043.15.
# If we subtract $359,362.15 (Site 136033 Ventas OWO) and $11,831.00 (Site 136034 Ventas APP Su Red) or other:
# Let's calculate: 6673043.15 - 359362.15 - 11831.00 = 6,301,850.00.
# Wait! 6,301,850.00 is still not 6,287,850.00. The difference is 6,301,850.00 - 6,287,850.00 = 14,000.00.
# Where does 14,000.00 come from?
# Wait! Let's check: 359,362.15 + 11,831.00 + 14,000.00 = 385,193.15.
# Let's search if there's another site or another chance sale that is app related, or if we have another unmapped site or other.
# Let's run a search for all chance sales for Rodrigo yesterday and see if we can find any sale with exactly 14,000.
# Or let's check all unmapped sites or other app sites.
