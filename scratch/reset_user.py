import sqlite3
import sys
import os

def reset_user(phone: str):
    db_path = os.path.join("uploads", "cache.db")
    if not os.path.exists(db_path):
        print(f"[ERROR] La base de datos no existe en: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Verificar si la tabla existe
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whatsapp_user_requests'")
        if not c.fetchone():
            print("[INFO] La tabla 'whatsapp_user_requests' aun no existe. El usuario puede interactuar libremente.")
            return

        # Borrar el registro del numero especifico
        c.execute("DELETE FROM whatsapp_user_requests WHERE phone = ?", (phone,))
        if c.rowcount > 0:
            conn.commit()
            print(f"[OK] Se borro con exito el registro del celular: {phone}")
            print(f"El proximo mensaje que envie este numero sera tratado como el 'primer mensaje del dia'.")
        else:
            print(f"[WARN] No se encontro ningun registro hoy para el celular: {phone}")

        conn.close()
    except Exception as e:
        print(f"[ERROR] Error al manipular la base de datos: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python reset_user.py <numero_de_celular>")
        print("Ejemplo: python reset_user.py 3153404327")
    else:
        phone_number = sys.argv[1]
        reset_user(phone_number)
