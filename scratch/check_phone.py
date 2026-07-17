import sqlite3

def check_number(phone):
    conn = sqlite3.connect("uploads/cache.db")
    c = conn.cursor()
    c.execute("SELECT name FROM whatsapp_administrators WHERE phone=?", (phone,))
    res = c.fetchone()
    if res:
        return f"{res[0]} (Admin)"
        
    c.execute("SELECT name FROM whatsapp_coordinators WHERE phone=?", (phone,))
    res = c.fetchone()
    if res:
        return f"{res[0]} (Coordinator)"
        
    c.execute("SELECT name FROM whatsapp_promoters WHERE phone=?", (phone,))
    res = c.fetchone()
    if res:
        return f"{res[0]} (Promoter)"
        
    return "Not Found"

print(check_number("573153404327"))
