import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")

# Let's inspect the distribution table schema in cache.db
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in cache.db:", tables)

# Let's query distribution or whatsapp_promoters
cursor.execute("PRAGMA table_info(whatsapp_promoters)")
print("whatsapp_promoters schema:", cursor.fetchall())

cursor.execute("SELECT * FROM whatsapp_promoters WHERE name LIKE '%Rodrigo%'")
print("Rodrigo in whatsapp_promoters:", cursor.fetchall())

# Let's see the goals database or distribution file if stored
# Wait, let's look at distribution.json or goals.json
DIST_FILE = os.path.join(BASE_DIR, "uploads", "distribution.json")
if os.path.exists(DIST_FILE):
    with open(DIST_FILE, "r", encoding="utf-8") as f:
        dist = json.load(f)
    print("\nSample records in distribution.json:")
    rodrigo_recs = [d for d in dist if "rodrigo" in str(d.get("promotor", "")).lower()]
    print(f"Total Rodrigo records: {len(rodrigo_recs)}")
    if rodrigo_recs:
        print("Columns in distribution record:", rodrigo_recs[0].keys())
        print("First few records:")
        for r in rodrigo_recs[:5]:
            print(r)
else:
    print("distribution.json not found")

conn.close()
