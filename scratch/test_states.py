import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import db_manager
import json

def test():
    db_manager.init_pools()
    try:
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ide_estado, SUM(vlr_pago_total) FROM GANA_SIGA.SIGT_VENTA_INCENTIVO_COBRO 
                WHERE fec_venta >= TO_DATE('2026-07-09 00:00:00', 'YYYY-MM-DD HH24:MI:SS') 
                  AND fec_venta < TO_DATE('2026-07-10 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
                  AND ide_producto = 21974
                GROUP BY ide_estado
            """)
            print('CAUCA PATA POR ESTADO:')
            for r in cursor.fetchall():
                print(f"Estado {r[0]}: {r[1]}")
                
            cursor.execute("""
                SELECT ide_estado, SUM(vlr_pago_total) FROM GANA_SIGA.SIGT_CHANCES
                WHERE fec_venta >= TO_DATE('2026-07-09 00:00:00', 'YYYY-MM-DD HH24:MI:SS') 
                  AND fec_venta < TO_DATE('2026-07-10 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
                  AND ide_producto = 1
                GROUP BY ide_estado
            """)
            print('CAUCA CHANCES POR ESTADO:')
            for r in cursor.fetchall():
                print(f"Estado {r[0]}: {r[1]}")
                
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    test()
