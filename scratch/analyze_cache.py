import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")
GOALS_FILE = os.path.join(BASE_DIR, "uploads", "goals.json")
DIST_FILE = os.path.join(BASE_DIR, "uploads", "distribution.json")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. Print all cache keys
cursor.execute("SELECT cache_key, last_updated FROM sales_cache")
rows = cursor.fetchall()
print("All Sales Cache Keys:")
for r in rows:
    print(f"Key: {r[0]} | Updated: {r[1]}")

# 2. Query catalog_sitios if it exists in sales_cache
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_sitios'")
row = cursor.fetchone()
if row:
    sitios = json.loads(row[0])
    print(f"\nTotal sitios in catalog_sitios: {len(sitios)}")
    # Find any sitio with Cod_Oficina = 333 or 334
    print("Sitios in office 333 or 334:")
    for s in sitios:
        off = s.get("Cod_Oficina")
        if off in [333, 334, "333", "334"]:
            print(s)
else:
    print("\nNo catalog_sitios in cache.")

# 3. Query catalog_productos
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_productos'")
row = cursor.fetchone()
if row:
    productos = json.loads(row[0])
    print(f"\nTotal products in catalog: {len(productos)}")
else:
    print("\nNo catalog_productos in cache.")

# 4. Search in goals.json for office 333 or 334
if os.path.exists(GOALS_FILE):
    print("\nReading goals.json to search for office 333/334...")
    with open(GOALS_FILE, "r", encoding="utf-8") as f:
        goals = json.load(f)
    print("Products in goals:", list(goals.keys()))
    found_333_334 = []
    for prod, records in goals.items():
        for r in records:
            if r.get("cod_oficina") in [333, 334, "333", "334"]:
                found_333_334.append((prod, r.get("fecha"), r.get("cod_oficina"), r.get("sitio_venta"), r.get("meta")))
    print(f"Found {len(found_333_334)} records in goals.json for offices 333 or 334.")
    if found_333_334:
        print("Sample records (up to 10):")
        for x in found_333_334[:10]:
            print(x)

# 5. Let's see if we have sales data for yesterday in any cache key
# Let's search inside sales_cache JSON content for any mentions of 333 or 334
cursor.execute("SELECT cache_key FROM sales_cache WHERE cache_key NOT IN ('catalog_sitios', 'catalog_productos')")
keys = [r[0] for r in cursor.fetchall()]
for k in keys:
    cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key = ?", (k,))
    data_json = cursor.fetchone()[0]
    sales = json.loads(data_json)
    print(f"\nChecking sales key: {k} (total sales rows: {len(sales)})")
    
    # We want to see if any sale has a site code that maps to office 333 or 334
    # But since we don't have the full mapping here, let's search if any site maps to 333/334 in the sales or if we can find site codes.
    # Actually, let's see if any site in the sales matches the site code of 333 or 334.
    # Let's list distinct Cod_Sitio in this sales list
    s_codes = set(s.get("Cod_Sitio") for s in sales if s.get("Cod_Sitio") is not None)
    print(f"Distinct site codes in sales: {len(s_codes)}")

conn.close()
