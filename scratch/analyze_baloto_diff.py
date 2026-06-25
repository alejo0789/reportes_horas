import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import get_ventas
from backend.db import db_manager
import json

def get_assigned_offices():
    try:
        with open('uploads/distribution.json') as f:
            distribution_store = json.load(f)
    except:
        distribution_store = []
    
    assigned_offices = set()
    for item in distribution_store:
        if item.get("cod_oficina") is not None:
            assigned_offices.add(int(item["cod_oficina"]))
    return assigned_offices

def get_site_to_office():
    try:
        import sqlite3
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
    # Manual OWO / APP
    site_to_office[333033] = 333
    site_to_office[334034] = 334
    return site_to_office

async def main():
    try:
        res = get_ventas(
            desde="2026-06-24 00:00:00",
            hasta="2026-06-24 23:59:59",
            force_refresh=False
        )
        sales = res.get("data", [])
        
        assigned_offices = get_assigned_offices()
        site_to_office = get_site_to_office()
        
        dashboard_baloto = 0.0
        whatsapp_baloto = 0.0
        
        for sale in sales:
            src_table = sale.get("Tabla_Origen")
            s_code = sale.get("Cod_Producto")
            
            # This is how backend handles product grouping
            # In backend: normalize_product uses code or Tabla_Origen
            is_baloto = False
            if str(s_code) == "22059" or src_table == "SIGT_BALOTO":
                is_baloto = True
                
            if is_baloto:
                # But wait, backend EXCLUDES SIGT_PAGOS and SIGT_PAGOGEN_MAESTRO
                if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
                    continue
                    
                v_neta = float(sale.get("Venta_Neta") or 0.0)
                
                # Dashboard includes EVERYTHING (unless filtered)
                dashboard_baloto += v_neta
                
                # WhatsApp includes ONLY assigned_offices!
                sitio = sale.get("Cod_Sitio")
                if sitio is not None:
                    off_code = site_to_office.get(int(sitio))
                    if off_code in assigned_offices:
                        whatsapp_baloto += v_neta
                        
        print(f"Total BALOTO Dashboard: {dashboard_baloto}")
        print(f"Total BALOTO WhatsApp: {whatsapp_baloto}")

    finally:
        pass

if __name__ == "__main__":
    asyncio.run(main())
