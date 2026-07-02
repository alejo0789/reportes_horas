import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager

def run_diagnostics():
    db_manager.init_pools()
    
    # 1. Count rows in SIGT_RECAUDOS_EMPRESAS
    query_empresas = """
    SELECT COUNT(*) 
    FROM GANA_SIGA.SIGT_RECAUDOS_EMPRESAS
    WHERE fec_venta >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_venta <  TO_DATE('2026-06-11 14:05:23', 'YYYY-MM-DD HH24:MI:SS')
      AND ide_estado IN (44)
    """
    
    # 2. Count rows in SIGT_RECAUDOS_MAESTRO (excluding 22005 CNB)
    query_maestro = """
    SELECT COUNT(*) 
    FROM GANA_SIGA.SIGT_RECAUDOS_MAESTRO
    WHERE fec_venta >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_venta <  TO_DATE('2026-06-11 14:05:23', 'YYYY-MM-DD HH24:MI:SS')
      AND ide_estado IN (61)
      AND ide_producto != 22005
    """

    for db_name in ["CAUCAMED", "FORTUMED"]:
        print(f"\n==========================================")
        print(f"DATABASE: {db_name}")
        print(f"==========================================")
        
        get_conn = db_manager.get_cauca_connection if db_name == "CAUCAMED" else db_manager.get_fortuna_connection
        
        try:
            with get_conn() as conn:
                cursor = conn.cursor()
                
                cursor.execute(query_empresas)
                cnt_emp = cursor.fetchone()[0]
                print(f"SIGT_RECAUDOS_EMPRESAS rows (state 44): {cnt_emp}")
                
                cursor.execute(query_maestro)
                cnt_mae = cursor.fetchone()[0]
                print(f"SIGT_RECAUDOS_MAESTRO rows (state 61, excl 22005): {cnt_mae}")
                
                print(f"Total: {cnt_emp + cnt_mae}")
                
                cursor.close()
        except Exception as e:
            print(f"Error en {db_name}: {e}")

if __name__ == "__main__":
    run_diagnostics()
