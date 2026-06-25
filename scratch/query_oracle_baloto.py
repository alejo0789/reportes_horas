import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import get_ventas
from backend.db import db_manager

async def main():
    try:
        db_manager.init_pools()
        print("Pools initialized. Querying Oracle for 2026-06-24...")
        
        res = get_ventas(
            desde="2026-06-24 00:00:00",
            hasta="2026-06-24 23:59:59",
            force_refresh=True
        )
        
        sales = res.get("data", [])
        print(f"Got {len(sales)} sales records.")
        
        # Calculate Baloto
        total_baloto = 0.0
        for s in sales:
            src_table = s.get("Tabla_Origen")
            if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
                continue
                
            # Backend logic maps SIGT_BALOTO or Cod_Producto
            if src_table == "SIGT_BALOTO" or str(s.get("Cod_Producto")) == "22059":
                total_baloto += float(s.get("Venta_Neta", 0.0))
                
        print(f"Total BALOTO in Oracle (raw sum): {total_baloto}")
        
    finally:
        db_manager.close_pools()

if __name__ == "__main__":
    asyncio.run(main())
