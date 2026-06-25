import sqlite3
import json

c = sqlite3.connect('uploads/cache.db').cursor()
c.execute("SELECT cache_key, last_updated FROM sales_cache ORDER BY last_updated DESC LIMIT 5")
print(c.fetchall())
