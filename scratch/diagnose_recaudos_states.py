import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager

def run_diagnostics():
    db_manager.init_pools()
    
    # Check states in SIGT_RECAUDOS_EMPRESAS
    query_emp_states = """
    SELECT ide_estado, COUNT(*) 
    FROM GANA_SIGA.SIGT_RECAUDOS_EMPRESAS
    WHERE fec_venta >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_venta <  TO_DATE('2026-06-11 14:05:23', 'YYYY-MM-DD HH24:MI:SS')
    GROUP BY ide_estado
    """
    
    # Check states in SIGT_RECAUDOS_MAESTRO
    query_mae_states = """
    SELECT ide_estado, COUNT(*) 
    FROM GANA_SIGA.SIGT_RECAUDOS_MAESTRO
    WHERE fec_venta >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_venta <  TO_DATE('2026-06-11 14:05:23', 'YYYY-MM-DD HH24:MI:SS')
    GROUP BY ide_estado
    """

    for db_name in ["CAUCAMED", "FORTUMED"]:
        print(f"\n==========================================")
        print(f"DATABASE: {db_name}")
        print(f"==========================================")
        
        get_conn = db_manager.get_cauca_connection if db_name == "CAUCAMED" else db_manager.get_fortuna_connection
        
        try:
            with get_conn() as conn:
                cursor = conn.cursor()
                
                print("--- SIGT_RECAUDOS_EMPRESAS States ---")
                cursor.execute(query_emp_states)
                for r in cursor.fetchall():
                    print(f"  State {r[0]}: {r[1]} rows")
                    
                print("--- SIGT_RECAUDOS_MAESTRO States ---")
                cursor.execute(query_mae_states)
                for r in cursor.fetchall():
                    print(f"  State {r[0]}: {r[1]} rows")
                
                cursor.close()
        except Exception as e:
            print(f"Error en {db_name}: {e}")

if __name__ == "__main__":
    run_diagnostics()
