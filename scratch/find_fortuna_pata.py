import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import db_manager

def test():
    db_manager.init_pools()
    try:
        with db_manager.get_fortuna_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ide_producto, des_producto FROM GANA_SIGA.SIGT_PRODUCTOS WHERE UPPER(des_producto) LIKE '%PATA%'")
            for r in cursor.fetchall():
                print('FORTUNA PATA EN CATALOGO:', r[0], r[1])
                
            cursor.execute("""
                SELECT ide_producto, SUM(vlr_pago_total) FROM GANA_SIGA.SIGT_VENTA_INCENTIVO_COBRO 
                WHERE fec_venta >= TO_DATE('2026-07-09 00:00:00', 'YYYY-MM-DD HH24:MI:SS') 
                  AND fec_venta < TO_DATE('2026-07-10 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
                  AND ide_estado IN (3)
                GROUP BY ide_producto
            """)
            print('FORTUNA VENTAS EN INCENTIVO COBRO:')
            for r in cursor.fetchall():
                print(f"Prod {r[0]}: {r[1]}")
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    test()
