import sqlite3
import json

conn = sqlite3.connect('uploads/cache.db')
cursor = conn.cursor()

cursor.execute("SELECT cache_key FROM sales_cache WHERE cache_key LIKE '2026-06-11%'")
rows = cursor.fetchall()
if rows:
    cache_key = rows[0][0]
    cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key=?", (cache_key,))
    data_json = cursor.fetchone()[0]
    sales = json.loads(data_json)
    if sales:
        print("Keys of first record:")
        print(sales[0])
else:
    print("No cache found.")

conn.close()
