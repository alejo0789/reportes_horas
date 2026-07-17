import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import db_manager

def test():
    db_manager.init_pools()
    try:
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT column_name FROM all_tab_columns WHERE table_name = 'SIGT_DOBLE_GANA'")
            print('Columnas en SIGT_DOBLE_GANA:', [r[0] for r in cursor.fetchall()])
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    test()
