import sqlite3
import json

conn = sqlite3.connect('uploads/cache.db')
c = conn.cursor()
c.execute("SELECT data_json FROM sales_cache WHERE cache_key = '2026-06-24 00:00:00_2026-06-24 23:59:59'")
row = c.fetchone()
conn.close()

if not row:
    print("No cache")
    exit()

sales_list = json.loads(row[0])

# Load distribution
try:
    with open('uploads/distribution.json') as f:
        distribution_store = json.load(f)
except:
    distribution_store = []

assigned_offices = set()
for item in distribution_store:
    if item.get("cod_oficina") is not None:
        assigned_offices.add(int(item["cod_oficina"]))

# Load sites to map site to office
try:
    c = sqlite3.connect('uploads/cache.db').cursor()
    c.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_sitios'")
    r = c.fetchone()
    sites_data = json.loads(r[0]) if r else []
except:
    sites_data = []

site_to_office = {}
for s in sites_data:
    s_code = s.get("Cod_Sitio")
    off_code = s.get("Cod_Oficina")
    if s_code is not None and off_code is not None:
        site_to_office[int(s_code)] = int(off_code)

total_baloto_all = 0.0
total_baloto_assigned = 0.0

for sale in sales_list:
    src_table = sale.get("Tabla_Origen")
    if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
        continue
        
    s_code = sale.get("Cod_Producto")
    is_baloto = False
    
    # check if it's baloto
    if s_code == 22059 or str(s_code) == "22059":
        is_baloto = True
    elif src_table == "SIGT_BALOTO":
        is_baloto = True
        
    if is_baloto:
        v_neta = float(sale.get("Venta_Neta") or 0.0)
        total_baloto_all += v_neta
        
        sitio = sale.get("Cod_Sitio")
        if sitio is not None:
            off = site_to_office.get(int(sitio))
            if off in assigned_offices:
                total_baloto_assigned += v_neta

print(f"Total BALOTO Dashboard (Todos los sitios): {total_baloto_all}")
print(f"Total BALOTO WhatsApp (Solo oficinas en distribución): {total_baloto_assigned}")
