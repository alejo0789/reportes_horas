import sqlite3
import json

conn = sqlite3.connect('uploads/cache.db')
c = conn.cursor()
c.execute("SELECT data_json FROM sales_cache WHERE cache_key = '2026-06-24 00:00:00_2026-06-24 23:59:59'")
row = c.fetchone()
conn.close()

if row:
    data = json.loads(row[0])
    if data:
        print("Keys:", data[0].keys())
        print("Sample:", data[0])
