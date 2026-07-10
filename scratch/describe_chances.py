import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import db_manager
import json

def describe():
    db_manager.init_pools()
    try:
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT column_name FROM all_tab_columns WHERE table_name = 'SIGT_CHANCES'")
            cols = [r[0] for r in cursor.fetchall()]
            print("Columnas en SIGT_CHANCES:")
            for c in cols:
                print(c)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    describe()
