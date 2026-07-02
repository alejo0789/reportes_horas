import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager
from backend.main import resolve_product_name

def calculate_recargas():
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

    total_recargas = 0.0
    recargas_breakdown = {}
    
    for r in all_rows:
        src_table = r.get("Tabla_Origen")
        if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
            continue
            
        prod_name = resolve_product_name(r, products_by_code)
        val = float(r.get("Venta_Neta") or 0.0)
        
        if prod_name == "RECARGA EN LINEA":
            total_recargas += val
            cod_prod = r.get("Cod_Producto")
            p_info = products_by_code.get(str(cod_prod)) or {}
            p_name = p_info.get("Producto", "Desconocido")
            recargas_breakdown[p_name] = recargas_breakdown.get(p_name, 0.0) + val
            
    print(f"Total RECARGA EN LINEA: ${total_recargas:,.2f}")
    print("--- Recargas Breakdown ---")
    for k, v in sorted(recargas_breakdown.items(), key=lambda x: -x[1]):
        print(f"  {k:<35}: ${v:,.2f}")

if __name__ == "__main__":
    calculate_recargas()
