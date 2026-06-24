import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager
from backend.main import resolve_product_name

def analyze_otros():
    db_manager.init_pools()
    
    products_by_code = {}
    with db_manager.get_cauca_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ide_producto, des_producto, ide_tipoproducto FROM GANA_SIGA.SIGT_PRODUCTOS")
        for r in cursor.fetchall():
            products_by_code[str(r[0])] = {"Producto": r[1], "Tipo_Producto": str(r[2])}
        cursor.close()

    from backend.queries import VENTAS_POR_HORA_QUERY
    desde = "2026-06-11 00:00:00"
    hasta = "2026-06-11 14:05:23"
    
    all_rows = []
    with db_manager.get_cauca_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            all_rows.append(dict(zip(columns, row)))
        cursor.close()

    with db_manager.get_fortuna_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            all_rows.append(dict(zip(columns, row)))
        cursor.close()

    breakdown = {}
    for r in all_rows:
        prod_name = resolve_product_name(r, products_by_code)
        if prod_name == "OTROS":
            cod_prod = r.get("Cod_Producto")
            val = float(r.get("Venta_Neta") or 0.0)
            p_info = products_by_code.get(str(cod_prod)) or {}
            p_name = p_info.get("Producto", "Desconocido")
            p_type = p_info.get("Tipo_Producto", "Desconocido")
            
            key = (cod_prod, p_name, p_type)
            breakdown[key] = breakdown.get(key, 0.0) + val
            
    print("--- Breakdown of 'OTROS' products by value ---")
    for (cod, name, ptype), val in sorted(breakdown.items(), key=lambda x: -x[1]):
        print(f"  Code {cod:<5} | {name:<35} | {ptype:<10} | ${val:,.2f}")

if __name__ == "__main__":
    analyze_otros()
