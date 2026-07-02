import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import db_manager

def run_diagnostics():
    db_manager.init_pools()
    
    # 1. Check all states in SIGT_SG_GIROS_CREADOS
    query_creados = """
    SELECT ide_producto, ide_estado, COUNT(*), SUM(valor_total)
    FROM GANA_SIGA.SIGT_SG_GIROS_CREADOS
    WHERE fec_giro >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_giro <  TO_DATE('2026-06-11 14:05:23', 'YYYY-MM-DD HH24:MI:SS')
    GROUP BY ide_producto, ide_estado
    """
    
    # 2. Check all states in SIGT_SG_GIROS_PAGADOS
    query_pagados = """
    SELECT ide_producto, ide_estado, COUNT(*), SUM(valor_total)
    FROM GANA_SIGA.SIGT_SG_GIROS_PAGADOS
    WHERE fec_pago >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_pago <  TO_DATE('2026-06-11 14:05:23', 'YYYY-MM-DD HH24:MI:SS')
    GROUP BY ide_producto, ide_estado
    """
    
    # 3. Check if there are other products related to GIRO in other tables
    query_recaudos_empresas = """
    SELECT ide_producto, COUNT(*)
    FROM GANA_SIGA.SIGT_RECAUDOS_EMPRESAS
    WHERE fec_venta >= TO_DATE('2026-06-11 00:00:00', 'YYYY-MM-DD HH24:MI:SS')
      AND fec_venta <  TO_DATE('2026-06-11 14:05:23', 'YYYY-MM-DD HH24:MI:SS')
      AND ide_producto IN (22061, 13, 14)
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
                
                print("--- GIROS CREADOS ---")
                cursor.execute(query_creados)
                print("Producto | Estado | Conteo | Suma Valor")
                for r in cursor.fetchall():
                    print(f"{r[0]} | {r[1]} | {r[2]} | ${r[3]:,.2f}")
                    
                print("\n--- GIROS PAGADOS ---")
                cursor.execute(query_pagados)
                print("Producto | Estado | Conteo | Suma Valor")
                for r in cursor.fetchall():
                    print(f"{r[0]} | {r[1]} | {r[2]} | ${r[3]:,.2f}")
                    
                print("\n--- SURED/GIROS EN RECAUDOS EMPRESAS ---")
                cursor.execute(query_recaudos_empresas)
                print("Producto | Conteo")
                for r in cursor.fetchall():
                    print(f"{r[0]} | {r[1]}")
                
                cursor.close()
        except Exception as e:
            print(f"Error en {db_name}: {e}")

if __name__ == "__main__":
    run_diagnostics()
