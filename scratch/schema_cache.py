import sqlite3

conn = sqlite3.connect('uploads/cache.db')
c = conn.cursor()
c.execute("PRAGMA table_info(sales_cache)")
print(c.fetchall())

conn.close()
