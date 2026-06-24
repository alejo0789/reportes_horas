import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager

def run_diagnostics():
    db_manager.init_pools()
    
    # 1. Count rows in SIGT_RECAUDOS_EMPRESAS up to 14:05:00
    query_empresas = """
    SELECT COUNT(*) 
    FROM GANA_SIGA.SIGT_RECAUDOS_EMPRESAS
    WHERE fec_venta >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_venta <  TO_DATE('2026-06-11 14:05:00', 'YYYY-MM-DD HH24:MI:SS')
      AND ide_estado IN (44)
    """
    
    # 2. Count rows in SIGT_RECAUDOS_MAESTRO (excl 22005 CNB and 35 Base Asesora) up to 14:05:00
    query_maestro = """
    SELECT COUNT(*) 
    FROM GANA_SIGA.SIGT_RECAUDOS_MAESTRO
    WHERE fec_venta >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_venta <  TO_DATE('2026-06-11 14:05:00', 'YYYY-MM-DD HH24:MI:SS')
      AND ide_estado IN (3)
      AND ide_producto NOT IN (22005, 35)
    """

    for db_name in ["CAUCAMED"]:
        try:
            with db_manager.get_cauca_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(query_empresas)
                cnt_emp = cursor.fetchone()[0]
                
                cursor.execute(query_maestro)
                cnt_mae = cursor.fetchone()[0]
                
                print(f"Al cortar exactamente a las 14:05:00 en CAUCAMED:")
                print(f"  SIGT_RECAUDOS_EMPRESAS (estado 44): {cnt_emp} transacciones")
                print(f"  SIGT_RECAUDOS_MAESTRO (estado 3, sin CNB ni Base Asesora): {cnt_mae} transacciones")
                print(f"  Suma Total: {cnt_emp + cnt_mae} transacciones")
                
                cursor.close()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_diagnostics()
