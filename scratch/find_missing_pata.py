import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import get_ventas, get_cached_sales
import json

def find_missing_products():
    print("Obteniendo ventas de ayer (2026-07-09)...")
    sales_resp = get_ventas(desde='2026-07-09 00:00:00', hasta='2026-07-09 23:59:59', force_refresh=True)
    
    cat, _ = get_cached_sales('catalog_productos')
    cat_dict = {str(c['Cod_Producto']): c for c in cat} if cat else {}
    
    product_sums = {}
    
    for s in sales_resp.get('data', []):
        t = str(s.get('Tabla_Origen', s.get('SRC_TABLE', s.get('src_table', 'UNKNOWN_TABLE'))))
        c = str(s.get('IDE_PRODUCTO', s.get('Cod_Producto', s.get('ide_producto'))))
        v = float(s.get('VENTA_NETA', s.get('Venta_Neta', s.get('venta_neta', 0))))
        
        name = cat_dict.get(c, {}).get('Producto', 'DESCONOCIDO (HUERFANO)')
        key = f"{t} | {c} - {name}"
        product_sums[key] = product_sums.get(key, 0) + v
            
    print("\n--- VENTAS TOTALES POR TABLA Y PRODUCTO ---")
    for name, total in sorted(product_sums.items(), key=lambda x: x[0]):
        print(f"{name}: {total}")
            
    print("\n--- VERIFICANDO CODIGOS CATALOGADOS QUE CONTIENEN 'PATA' ---")
    for c_str, info in cat_dict.items():
        if 'PATA' in str(info.get('Producto', '')).upper():
            print(f"En Catalogo: {c_str} -> {info.get('Producto')}")

if __name__ == "__main__":
    find_missing_products()
