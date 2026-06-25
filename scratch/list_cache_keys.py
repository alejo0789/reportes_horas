import sqlite3

conn = sqlite3.connect('uploads/cache.db')
c = conn.cursor()
c.execute("SELECT cache_key, last_updated FROM sales_cache")
print(c.fetchall())
conn.close()
