import sys
import os
import asyncio
import json
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import get_ventas
from backend.db import db_manager

def main():
    try:
        with open('uploads/distribution.json') as f:
            distribution_store = json.load(f)
    except:
        distribution_store = []
    
    assigned_offices = set()
    for item in distribution_store:
        if item.get("cod_oficina") is not None:
            assigned_offices.add(int(item["cod_oficina"]))

    c = sqlite3.connect('uploads/cache.db').cursor()
    c.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_sitios'")
    r = c.fetchone()
    sites_data = json.loads(r[0]) if r else []

    site_to_office = {}
    for s in sites_data:
        s_code = s.get("Cod_Sitio")
        off_code = s.get("Cod_Oficina")
        if s_code is not None and off_code is not None:
            site_to_office[int(s_code)] = int(off_code)
    site_to_office[333033] = 333
    site_to_office[334034] = 334

    res = get_ventas(
        desde="2026-06-24 00:00:00",
        hasta="2026-06-24 23:59:59",
        force_refresh=False
    )
    sales = res.get("data", [])
    
    missing_offices = {}
    
    for sale in sales:
        src_table = sale.get("Tabla_Origen")
        s_code = sale.get("Cod_Producto")
        
        is_baloto = False
        if str(s_code) == "22059" or src_table == "SIGT_BALOTO":
            is_baloto = True
            
        if is_baloto:
            if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
                continue
                
            v_neta = float(sale.get("Venta_Neta") or 0.0)
            
            sitio = sale.get("Cod_Sitio")
            if sitio is not None:
                off_code = site_to_office.get(int(sitio))
                if off_code not in assigned_offices:
                    missing_offices[off_code] = missing_offices.get(off_code, 0) + v_neta
                    
    print(f"Missing offices contributing to the 24,000 difference:")
    for off, val in missing_offices.items():
        print(f"Oficina {off}: {val}")

if __name__ == "__main__":
    main()
