import sys
sys.path.append('.')
from backend.db import db_manager
from backend.main import get_ventas

def main():
    db_manager.init_pools()
    print("Refrescando cache Diario del 8 de julio...")
    get_ventas(desde="2026-07-08 00:00:00", hasta="2026-07-08 23:59:59", force_refresh=True)
    
    print("Refrescando cache Mensual del 8 de julio...")
    get_ventas(desde="2026-07-01 00:00:00", hasta="2026-07-08 23:59:59", force_refresh=True)

    print("Cachés refrescados con éxito.")

main()
