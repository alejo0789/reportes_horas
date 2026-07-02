import os
import sys
# Add workspace root to sys.path so we can import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager

def run_oracle_queries():
    db_manager.init_pools()
    
    query = """
    SELECT ide_producto, ide_estado, COUNT(*), SUM(valor_total)
    FROM GANA_SIGA.SIGT_SG_GIROS_CREADOS
    WHERE fec_giro >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_giro <  TO_DATE('2026-06-12 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
    GROUP BY ide_producto, ide_estado
    """
    
    print("--- CONSULTANDO CAUCAMED ---")
    try:
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            print("Producto | Estado | Conteo | Suma Valor Total")
            print("-" * 50)
            for r in rows:
                print(f"{r[0]} | {r[1]} | {r[2]} | ${r[3]:,.2f}")
    except Exception as e:
        print(f"Error en CAUCAMED: {e}")
        
    print("\n--- CONSULTANDO FORTUMED ---")
    try:
        with db_manager.get_fortuna_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            print("Producto | Estado | Conteo | Suma Valor Total")
            print("-" * 50)
            for r in rows:
                print(f"{r[0]} | {r[1]} | {r[2]} | ${r[3]:,.2f}")
    except Exception as e:
        print(f"Error en FORTUMED: {e}")

if __name__ == "__main__":
    run_oracle_queries()
