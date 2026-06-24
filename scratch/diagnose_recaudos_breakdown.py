import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager

def run_diagnostics():
    db_manager.init_pools()
    
    query_maestro_breakdown = """
    SELECT ide_producto, COUNT(*)
    FROM GANA_SIGA.SIGT_RECAUDOS_MAESTRO
    WHERE fec_venta >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_venta <  TO_DATE('2026-06-11 14:05:23', 'YYYY-MM-DD HH24:MI:SS')
      AND ide_estado = 3
    GROUP BY ide_producto
    """

    for db_name in ["CAUCAMED", "FORTUMED"]:
        print(f"\n==========================================")
        print(f"DATABASE: {db_name}")
        print(f"==========================================")
        
        get_conn = db_manager.get_cauca_connection if db_name == "CAUCAMED" else db_manager.get_fortuna_connection
        
        try:
            with get_conn() as conn:
                cursor = conn.cursor()
                
                print("--- SIGT_RECAUDOS_MAESTRO breakdown ---")
                cursor.execute(query_maestro_breakdown)
                total_excl_cnb = 0
                for r in cursor.fetchall():
                    print(f"  Producto {r[0]}: {r[1]} rows")
                    if r[0] != 22005:
                        total_excl_cnb += r[1]
                print(f"Total excluding CNB (22005): {total_excl_cnb}")
                
                cursor.close()
        except Exception as e:
            print(f"Error en {db_name}: {e}")

if __name__ == "__main__":
    run_diagnostics()
