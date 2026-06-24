import sqlite3
import json

conn = sqlite3.connect('uploads/cache.db')
cursor = conn.cursor()

# Find the cache key for today
cursor.execute("SELECT cache_key FROM sales_cache WHERE cache_key LIKE '2026-06-11%'")
rows = cursor.fetchall()
if not rows:
    print("No cache found for today (2026-06-11).")
    conn.close()
    exit()

cache_key = rows[0][0]
print(f"Using cache key: {cache_key}")

cursor.execute("SELECT data_json, last_updated FROM sales_cache WHERE cache_key=?", (cache_key,))
data_json, last_updated = cursor.fetchone()
sales_list = json.loads(data_json)
print(f"Loaded {len(sales_list)} sales rows. Last updated: {last_updated}")

# Load product and site catalogs to match
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key='catalog_sitios'")
sitios_row = cursor.fetchone()
site_to_office = {}
office_to_info = {}
if sitios_row:
    for s in json.loads(sitios_row[0]):
        s_code = s.get("Cod_Sitio")
        off_code = s.get("Cod_Oficina")
        off_name = s.get("Oficina")
        zona = s.get("Zona")
        if s_code is not None and off_code is not None:
            site_to_office[int(s_code)] = int(off_code)
            office_to_info[int(off_code)] = {"name": off_name, "zona": zona}

cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key='catalog_productos'")
prod_row = cursor.fetchone()
products_by_code = {}
if prod_row:
    for p in json.loads(prod_row[0]):
        products_by_code[str(p["Cod_Producto"])] = p

# Let's count GIROS by zone and office
total_giros = 0
giros_by_zone = {}
giros_by_office = {}
unmapped_sites = {}

for sale in sales_list:
    src_table = sale.get("Tabla_Origen")
    if src_table != 'SIGT_SG_GIROS_CREADOS':
        continue
    
    val = float(sale.get("Venta_Neta") or 0.0)
    total_giros += val
    
    s_code = sale.get("Cod_Sitio")
    if s_code is not None:
        s_code_int = int(s_code)
        off_code = site_to_office.get(s_code_int)
        if off_code is not None:
            info = office_to_info.get(off_code)
            zona = info["zona"] if info else "Sin Zona"
            off_name = info["name"] if info else f"Oficina {off_code}"
            
            giros_by_zone[zona] = giros_by_zone.get(zona, 0.0) + val
            giros_by_office[off_name] = giros_by_office.get(off_name, 0.0) + val
        else:
            unmapped_sites[s_code_int] = unmapped_sites.get(s_code_int, 0.0) + val

print(f"\nTotal GIROS in Cache: {total_giros}")
print("\nGIROS by Zone:")
for z, count in sorted(giros_by_zone.items(), key=lambda x: -x[1]):
    print(f"  {z}: {count}")

print("\nGIROS by Office (Top 10):")
for o, count in sorted(giros_by_office.items(), key=lambda x: -x[1])[:10]:
    print(f"  {o}: {count}")

if unmapped_sites:
    print(f"\nGIROS on Unmapped Sites (Total: {sum(unmapped_sites.values())}):")
    for s, count in sorted(unmapped_sites.items(), key=lambda x: -x[1]):
        print(f"  Site {s}: {count}")

conn.close()
