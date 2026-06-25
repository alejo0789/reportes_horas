import sqlite3

conn = sqlite3.connect('uploads/cache.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("Tables:", tables)

if ('cache_ventas',) in tables:
    c.execute("PRAGMA table_info(cache_ventas)")
    print("Schema of cache_ventas:", c.fetchall())

conn.close()
