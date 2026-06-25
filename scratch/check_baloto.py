import sqlite3
import pandas as pd

conn = sqlite3.connect('uploads/cache.db')
query = """
SELECT Cod_Producto, SUM(Venta_Neta) as Total_Venta
FROM cache_ventas
WHERE Tabla_Origen = 'SIGT_BALOTO' 
  AND Timestamp >= '2026-06-24 00:00:00' 
  AND Timestamp <= '2026-06-24 23:59:59'
GROUP BY Cod_Producto
"""
df = pd.read_sql_query(query, conn)
print("Ventas en cache_ventas de SIGT_BALOTO:")
print(df)

query_total = """
SELECT SUM(Venta_Neta) as Total
FROM cache_ventas
WHERE Tabla_Origen = 'SIGT_BALOTO' 
  AND Timestamp >= '2026-06-24 00:00:00' 
  AND Timestamp <= '2026-06-24 23:59:59'
"""
df_total = pd.read_sql_query(query_total, conn)
print("\nTotal en cache_ventas:", df_total['Total'].iloc[0])

query_all = """
SELECT Tabla_Origen, SUM(Venta_Neta) as Total
FROM cache_ventas
WHERE Timestamp >= '2026-06-24 00:00:00' 
  AND Timestamp <= '2026-06-24 23:59:59'
  AND Tabla_Origen LIKE '%BALOTO%'
GROUP BY Tabla_Origen
"""
df_all = pd.read_sql_query(query_all, conn)
print("\nOtras tablas de BALOTO:")
print(df_all)

conn.close()
