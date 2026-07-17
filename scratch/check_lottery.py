import sys
sys.path.append('.')
from backend.db import db_manager

def main():
    db_manager.init_pools()
    if not db_manager.pool_cauca or not db_manager.pool_fortuna:
        print("No se pudo conectar a Oracle")
        return

    from backend.queries import VENTAS_POR_HORA_QUERY

    total_by_src = {}
    total_by_prod = {}
    
    for db_name, pool in [("CAUCA", db_manager.get_cauca_connection), ("FORTUNA", db_manager.get_fortuna_connection)]:
        with pool() as conn:
            with conn.cursor() as cursor:
                cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": "2026-07-08 00:00:00", "hasta": "2026-07-09 00:00:00"})
                for row in cursor:
                    # row: Cod_Sitio, Fecha, Cod_Producto, Fecha_Dia, Hora, Tabla_Origen, Venta_Neta
                    prod = row[2]
                    src = row[5]
                    val = row[6]
                    total_by_src[src] = total_by_src.get(src, 0) + val
                    total_by_prod[prod] = total_by_prod.get(prod, 0) + val

    print("--- VENTAS POR TABLA ---")
    for src, val in sorted(total_by_src.items(), key=lambda x: -x[1]):
        print(f"{src}: {val}")
        
    print("\n--- VENTAS POR PRODUCTO ---")
    for prod, val in sorted(total_by_prod.items(), key=lambda x: -x[1]):
        print(f"Prod {prod}: {val}")

main()
