import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import db_manager

def test():
    db_manager.init_pools()
    try:
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(vlr_pago_total) FROM GANA_SIGA.SIGT_CHANCES
                WHERE fec_venta >= TO_DATE('2026-07-09 00:00:00', 'YYYY-MM-DD HH24:MI:SS') 
                  AND fec_venta < TO_DATE('2026-07-10 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
                  AND ide_estado IN (8)
            """)
            print('CAUCA CHANCES CANCELADOS (ESTADO 8):', cursor.fetchone()[0])
            
        with db_manager.get_fortuna_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(vlr_pago_total) FROM GANA_SIGA.SIGT_CHANCES
                WHERE fec_venta >= TO_DATE('2026-07-09 00:00:00', 'YYYY-MM-DD HH24:MI:SS') 
                  AND fec_venta < TO_DATE('2026-07-10 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
                  AND ide_estado IN (8)
            """)
            print('FORTUNA CHANCES CANCELADOS (ESTADO 8):', cursor.fetchone()[0])
            
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    test()
