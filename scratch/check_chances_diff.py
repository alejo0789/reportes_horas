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
                SELECT SUM(vlr_pago_total), SUM(vlr_apostado), SUM(vlr_iva)
                FROM GANA_SIGA.SIGT_CHANCES
                WHERE fec_venta >= TO_DATE('2026-07-09 00:00:00', 'YYYY-MM-DD HH24:MI:SS') 
                  AND fec_venta < TO_DATE('2026-07-10 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
                  AND ide_estado IN (3)
            """)
            row = cursor.fetchone()
            print('CAUCA CHANCES:')
            print('Pago Total:', row[0])
            print('Apostado:', row[1])
            print('IVA:', row[2])
            print('Diferencia (Total - Apostado - IVA):', row[0] - row[1] - (row[2] or 0))
            
        with db_manager.get_fortuna_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(vlr_pago_total), SUM(vlr_apostado), SUM(vlr_iva)
                FROM GANA_SIGA.SIGT_CHANCES
                WHERE fec_venta >= TO_DATE('2026-07-09 00:00:00', 'YYYY-MM-DD HH24:MI:SS') 
                  AND fec_venta < TO_DATE('2026-07-10 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
                  AND ide_estado IN (3)
            """)
            row = cursor.fetchone()
            print('FORTUNA CHANCES:')
            print('Pago Total:', row[0])
            print('Apostado:', row[1])
            print('IVA:', row[2])
            print('Diferencia (Total - Apostado - IVA):', row[0] - row[1] - (row[2] or 0))
            
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    test()
