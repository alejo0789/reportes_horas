import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager

def run_diagnostics():
    db_manager.init_pools()
    
    query = """
    SELECT ide_producto, COUNT(*)
    FROM GANA_SIGA.SIGT_RECAUDOS_MAESTRO
    WHERE fec_venta >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_venta <  TO_DATE('2026-06-11 14:05:00', 'YYYY-MM-DD HH24:MI:SS')
      AND ide_estado = 3
    GROUP BY ide_producto
    """

    try:
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            for r in cursor.fetchall():
                print(f"Producto {r[0]}: {r[1]} rows")
            cursor.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_diagnostics()
