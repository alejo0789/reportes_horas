import sys
import os
import argparse
from datetime import datetime

# Adjust path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import db_manager
from backend.queries import VENTAS_POR_HORA_QUERY
from backend.cache import set_cached_sales

def main():
    parser = argparse.ArgumentParser(description="Actualiza la caché de ventas para una fecha y hasta una hora específica.")
    parser.add_argument("--fecha", default=datetime.now().strftime("%Y-%m-%d"), help="Fecha YYYY-MM-DD (por defecto hoy)")
    parser.add_argument("--hora", default="17:12", help="Hora límite HH:MM (por defecto 17:12)")
    
    args = parser.parse_args()
    
    fecha = args.fecha
    hora = args.hora
    
    desde = f"{fecha} 00:00:00"
    hasta_consulta = f"{fecha} {hora}:00"
    # La clave de caché que busca el dashboard web y los reportes (día completo)
    cache_key = f"{fecha} 00:00:00_{fecha} 23:59:59"
    
    print(f"Iniciando consulta para {fecha} hasta las {hora}...")
    print(f"Rango de consulta a Oracle: {desde} hasta {hasta_consulta}")
    print(f"Se guardará en la caché local con la clave: {cache_key}")
    
    db_manager.init_pools()
    
    results = []
    
    # Consulta a CAUCAMED
    if db_manager.pool_cauca:
        try:
            with db_manager.get_cauca_connection() as conn:
                with conn.cursor() as cursor:
                    print("Consultando CAUCAMED...")
                    cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta_consulta})
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    count = 0
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        row_dict["Fuente"] = "CAUCA"
                        results.append(row_dict)
                        count += 1
                    print(f"CAUCAMED retornó {count} registros.")
        except Exception as e:
            print(f"Error al consultar CAUCAMED: {e}")
    else:
        print("El pool de CAUCAMED no está inicializado.")

    # Consulta a FORTUMED
    if db_manager.pool_fortuna:
        try:
            with db_manager.get_fortuna_connection() as conn:
                with conn.cursor() as cursor:
                    print("Consultando FORTUMED...")
                    cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta_consulta})
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    count = 0
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        row_dict["Fuente"] = "FORTUNA"
                        results.append(row_dict)
                        count += 1
                    print(f"FORTUMED retornó {count} registros.")
        except Exception as e:
            print(f"Error al consultar FORTUMED: {e}")
    else:
        print("El pool de FORTUMED no está inicializado.")
    
    db_manager.close_pools()
    
    if results:
        set_cached_sales(cache_key, results)
        print(f"\n¡Éxito! Se han guardado {len(results)} registros de ventas en la caché local para {fecha}.")
    else:
        print("\nNo se obtuvieron registros de ninguna de las bases de datos. No se actualizó la caché.")

if __name__ == "__main__":
    main()
