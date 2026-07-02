import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager
from backend.main import resolve_product_name

def calculate_frontend_sales():
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

    total_sales_overall = 0.0
    total_sales_excluding_count = 0.0
    by_product = {}
    
    for r in all_rows:
        src_table = r.get("Tabla_Origen")
        if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
            continue
            
        prod_name = resolve_product_name(r, products_by_code)
        val = float(r.get("Venta_Neta") or 0.0)
        
        by_product[prod_name] = by_product.get(prod_name, 0.0) + val
        total_sales_overall += val
        
        if prod_name not in {"GIROS", "TRANSACCIONES CNB", "RECAUDOS EMPRESARIALES"}:
            total_sales_excluding_count += val
            
    print("--- Frontend Sales by Category ---")
    for prod, sum_val in sorted(by_product.items(), key=lambda x: -x[1]):
        print(f"  {prod:<25}: ${sum_val:,.2f}")
        
    print(f"\nTotal overall sales: ${total_sales_overall:,.2f}")
    print(f"Total sales excluding GIROS, CNB, RECAUDOS: ${total_sales_excluding_count:,.2f}")

if __name__ == "__main__":
    calculate_frontend_sales()
