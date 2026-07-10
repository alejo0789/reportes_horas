import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import get_ventas, get_cached_sales
import json

def find_missing_products():
    print("Obteniendo ventas de ayer (2026-07-09)...")
    sales_resp = get_ventas(desde='2026-07-09 00:00:00', hasta='2026-07-09 23:59:59', force_refresh=False)
    
    cat, _ = get_cached_sales('catalog_productos')
    cat_dict = {str(c['Cod_Producto']): c for c in cat} if cat else {}
    
    unknown_chance_codes = {}
    
    for s in sales_resp.get('data', []):
        if s.get('Tabla_Origen', s.get('SRC_TABLE', s.get('src_table'))) == 'SIGT_CHANCES':
            c = str(s.get('IDE_PRODUCTO', s.get('Cod_Producto', s.get('ide_producto'))))
            v = float(s.get('VENTA_NETA', s.get('Venta_Neta', s.get('venta_neta', 0))))
            
            if c not in cat_dict:
                unknown_chance_codes[c] = unknown_chance_codes.get(c, 0) + v
                
    print("\n--- CODIGOS DE PRODUCTO EN SIGT_CHANCES QUE NO ESTAN EN EL CATALOGO ---")
    if not unknown_chance_codes:
        print("No se encontraron codigos huerfanos. El problema podria ser otro.")
    else:
        for code, total in unknown_chance_codes.items():
            print(f"Cod_Producto: {code} -> Total Venta_Neta: {total}")
            
    print("\n--- VERIFICANDO CODIGOS CATALOGADOS QUE CONTIENEN 'PATA' ---")
    for c_str, info in cat_dict.items():
        if 'PATA' in str(info.get('Producto', '')).upper():
            print(f"En Catalogo: {c_str} -> {info.get('Producto')}")

if __name__ == "__main__":
    find_missing_products()
