import sqlite3
import os

db_path = "uploads/cache.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Let's see what is there before
    cursor.execute("SELECT id, name, zone FROM whatsapp_coordinators WHERE name LIKE '%YUDY%'")
    rows = cursor.fetchall()
    print("Before update:", rows)
    
    # Update zone to "Oriente y municipios Centro"
    cursor.execute(
        "UPDATE whatsapp_coordinators SET zone = 'Oriente y municipios Centro' WHERE name LIKE '%YUDY%'"
    )
    conn.commit()
    
    # Verify the update
    cursor.execute("SELECT id, name, zone FROM whatsapp_coordinators WHERE name LIKE '%YUDY%'")
    rows = cursor.fetchall()
    print("After update:", rows)
    
    conn.close()
else:
    print("Database not found!")
