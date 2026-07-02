import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager

def run_diagnostics():
    db_manager.init_pools()
    
    query_prod_breakdown = """
    SELECT t.ide_producto, COUNT(*), SUM(t.vlr_pago_total), SUM(t.vlr_apostado), SUM(t.vlr_iva)
    FROM GANA_SIGA.SIGT_VENTA_INCENTIVO_COBRO t
    WHERE t.fec_venta >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND t.fec_venta <  TO_DATE('2026-06-11 14:05:23', 'YYYY-MM-DD HH24:MI:SS')
      AND t.ide_estado = 3
    GROUP BY t.ide_producto
    """

    try:
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(query_prod_breakdown)
            for r in cursor.fetchall():
                print(f"Producto {r[0]}: Count={r[1]}, Sum(vlr_pago_total)={r[2]}, Sum(vlr_apostado)={r[3]}, Sum(vlr_iva)={r[4]}")
                
            cursor.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_diagnostics()
