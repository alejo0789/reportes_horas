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
for s in sitios_data:
    s_code = s.get("Cod_Sitio")
    off_code = s.get("Cod_Oficina")
    if s_code is not None:
        site_to_office[int(s_code)] = int(off_code) if off_code is not None else None

for s in sales:
    src_table = s.get("Tabla_Origen")
    if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
        continue
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
    site_code = int(site_code)
    if site_code not in site_to_office:
        print(f"Unmapped site in sales: {s}")
