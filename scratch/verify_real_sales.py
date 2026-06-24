import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager
from backend.main import resolve_product_name

def verify_real_sales():
    db_manager.init_pools()
    
    # We query the catalog first
    products_by_code = {}
    try:
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ide_producto, des_producto, ide_tipoproducto FROM GANA_SIGA.SIGT_PRODUCTOS")
            for r in cursor.fetchall():
                products_by_code[str(r[0])] = {"Producto": r[1], "Tipo_Producto": str(r[2])}
            cursor.close()
    except Exception as e:
        print(f"Error fetching catalog: {e}")
        return

    # Let's run a query to fetch all transaction values from Oracle for today up to 14:05:23
    from backend.queries import VENTAS_POR_HORA_QUERY
    desde = "2026-06-11 00:00:00"
    hasta = "2026-06-11 14:05:23"
    
    all_rows = []
    
    # CAUCAMED
    try:
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
            
            # Convert to dicts
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                all_rows.append(dict(zip(columns, row)))
            cursor.close()
    except Exception as e:
        print(f"Error querying CAUCAMED: {e}")

    # FORTUMED
    try:
        with db_manager.get_fortuna_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
            
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                all_rows.append(dict(zip(columns, row)))
            cursor.close()
    except Exception as e:
        print(f"Error querying FORTUMED: {e}")

    print(f"Query returned {len(all_rows)} total records.")
    
    # Calculate totals
    total_monetary_sales = 0.0
    by_product = {}
    
    for r in all_rows:
        prod_name = resolve_product_name(r, products_by_code)
        val = float(r.get("Venta_Neta") or 0.0)
        
        # Exclude count-based
        if prod_name not in {"GIROS", "TRANSACCIONES CNB", "RECAUDOS EMPRESARIALES"}:
            total_monetary_sales += val
            
        by_product[prod_name] = by_product.get(prod_name, 0.0) + val
        
    print("\n--- Sales breakdown by product in Oracle (up to 14:05:23) ---")
    for prod, sum_val in sorted(by_product.items(), key=lambda x: -x[1]):
        print(f"  {prod:<25}: ${sum_val:,.2f}")
        
    print(f"\nTotal sales excluding count-based: ${total_monetary_sales:,.2f}")

if __name__ == "__main__":
    verify_real_sales()
