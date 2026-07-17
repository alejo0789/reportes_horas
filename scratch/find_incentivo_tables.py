import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import db_manager

def test():
    db_manager.init_pools()
    try:
        with db_manager.get_cauca_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM all_tables WHERE table_name LIKE '%INCENTIVO%'")
            print('CAUCA INCENTIVOS:', [r[0] for r in cursor.fetchall()])
            
        with db_manager.get_fortuna_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM all_tables WHERE table_name LIKE '%INCENTIVO%'")
            print('FORTUNA INCENTIVOS:', [r[0] for r in cursor.fetchall()])
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    test()
