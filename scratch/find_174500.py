import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import db_manager

def test():
    db_manager.init_pools()
    try:
        totals = {}
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ide_producto, SUM(vlr_pago_total) FROM GANA_SIGA.SIGT_CHANCES
                WHERE fec_venta >= TO_DATE('2026-07-09 00:00:00', 'YYYY-MM-DD HH24:MI:SS') 
                  AND fec_venta < TO_DATE('2026-07-10 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
                  AND ide_estado IN (3)
                GROUP BY ide_producto
            """)
            for r in cursor.fetchall():
                totals[f"CAUCA CHANCES {r[0]}"] = r[1]
                
        with db_manager.get_fortuna_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ide_producto, SUM(vlr_pago_total) FROM GANA_SIGA.SIGT_CHANCES
                WHERE fec_venta >= TO_DATE('2026-07-09 00:00:00', 'YYYY-MM-DD HH24:MI:SS') 
                  AND fec_venta < TO_DATE('2026-07-10 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
                  AND ide_estado IN (3)
                GROUP BY ide_producto
            """)
            for r in cursor.fetchall():
                totals[f"FORTUNA CHANCES {r[0]}"] = r[1]
                
        for k, v in sorted(totals.items(), key=lambda x: x[1]):
            print(f"{k}: {v}")
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    test()
