import sqlite3
import json
import pandas as pd

conn = sqlite3.connect('uploads/cache.db')
c = conn.cursor()
c.execute("SELECT data_json FROM sales_cache WHERE cache_key = '2026-06-24 00:00:00_2026-06-24 23:59:59'")
row = c.fetchone()
conn.close()

if row:
    data = json.loads(row[0])
    
    # Same logic as main.py
    sales_total = 0.0
    for sale in data:
        # What does main.py do?
        src_table = sale.get("Tabla_Origen")
        if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
            continue
            
        prod_code = sale.get("Cod_Producto")
        # In main.py, it matches by prod_name from catalog. 
        # But wait, BALOTO might be filtered differently?
        
        # Let's just group by Tabla_Origen and check the sum
        if "BALOTO" in str(src_table):
            sales_total += float(sale.get("Venta_Neta", 0.0))
            
    print("Total Venta_Neta para Tabla_Origen LIKE '%BALOTO%' en cache JSON:", sales_total)
    
    # Group by exact Tabla_Origen
    df = pd.DataFrame(data)
    if not df.empty:
        baloto_df = df[df['Tabla_Origen'].str.contains('BALOTO', na=False, case=False)]
        print(baloto_df.groupby('Tabla_Origen')['Venta_Neta'].sum())
else:
    print("No cache found for 2026-06-24")
