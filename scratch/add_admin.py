import sqlite3
conn = sqlite3.connect('uploads/cache.db')
c = conn.cursor()
c.execute("INSERT OR REPLACE INTO whatsapp_administrators (id, name, phone, active) VALUES (100, 'Test User', '573153404327', 1)")
conn.commit()
print('Added 573153404327 as Admin')
