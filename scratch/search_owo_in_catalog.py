import json
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_sitios'")
sitios_data = json.loads(cursor.fetchone()[0])
conn.close()

target_offices = {134, 136, 138, 167, 333, 334}
found = []
for s in sitios_data:
    off = s.get("Cod_Oficina")
    name = str(s.get("Sitio_Venta", "")).upper()
    code = s.get("Cod_Sitio")
    if off in target_offices or "OWO" in name or "APP" in name or "SURED" in name or "SU RED" in name:
        found.append(s)

print(f"Found {len(found)} sites in catalog:")
for s in sorted(found, key=lambda x: (x.get("Cod_Oficina") or 0, x.get("Cod_Sitio") or 0)):
    print(f"Office: {s.get('Cod_Oficina')} | Code: {s.get('Cod_Sitio')} | Name: {s.get('Sitio_Venta')}")
