import sqlite3
import os

def main():
    # Ruta a la base de datos de caché
    db_path = os.path.join(os.path.dirname(__file__), 'uploads', 'cache.db')
    
    if not os.path.exists(db_path):
        print(f"Error: No se encontró la base de datos en {db_path}")
        return

    print("=== LIMPIAR SESIÓN DE WHATSAPP ===")
    print("Esto hará que el bot olvide la conversación de hoy y vuelva a enviar el ciclo de AYER.")
    numero = input("Ingresa el número de teléfono (ej: 3153404327): ").strip()
    
    if not numero:
        print("Número no válido.")
        return
        
    # Asegurar que tenga el prefijo 57 si el usuario ingresó solo los 10 dígitos (Colombia)
    if len(numero) == 10:
        numero = "57" + numero

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si el número existe en la base de datos
        cursor.execute("SELECT last_date, date_context FROM whatsapp_user_requests WHERE phone = ?", (numero,))
        row = cursor.fetchone()
        
        if row:
            # Borrar el registro
            cursor.execute("DELETE FROM whatsapp_user_requests WHERE phone = ?", (numero,))
            conn.commit()
            print(f"\n✅ ¡Éxito! El estado del número {numero} ha sido borrado.")
            print(f"Estado anterior -> Fecha: {row[0]}, Ciclo: {row[1]}")
            print("El próximo mensaje que envíe este número iniciará el ciclo de AYER de nuevo.")
        else:
            print(f"\n⚠️ No se encontró ninguna sesión activa para el número {numero}.")
            print("Esto significa que para el bot, este número ya está listo para iniciar como si fuera su primer mensaje.")
            
    except sqlite3.OperationalError as e:
        print(f"\n❌ Ocurrió un error con la base de datos: {e}")
        print("Asegúrate de que la tabla 'whatsapp_user_requests' exista.")
    except Exception as e:
        print(f"\n❌ Ocurrió un error inesperado: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
