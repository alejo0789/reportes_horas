import os
import json
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")
DIST_FILE = os.path.join(BASE_DIR, "uploads", "distribution.json")
GOALS_FILE = os.path.join(BASE_DIR, "uploads", "goals.json")

print("DB Path:", DB_PATH)
print("Distribution File:", DIST_FILE)

# 1. Search for Rodrigo Ledezma in promoters db
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM whatsapp_promoters WHERE name LIKE '%Ledezma%' OR name LIKE '%Rodrigo%'")
    rows = cursor.fetchall()
    print("Promoters in DB matching 'Ledezma' or 'Rodrigo':")
    for r in rows:
        print(r)
    conn.close()

# 2. Search in distribution.json for Rodrigo Ledezma
if os.path.exists(DIST_FILE):
    with open(DIST_FILE, "r", encoding="utf-8") as f:
        dist = json.load(f)
    print("\nMatching records in distribution.json:")
    rodrigo_offices = []
    for r in dist:
        promotor = r.get("promotor", "")
        if "ledezma" in promotor.lower() or "rodrigo" in promotor.lower():
            print(r)
            rodrigo_offices.append(r)
    
    print("\nRodrigo's assigned office codes:", [r.get("cod_oficina") for r in rodrigo_offices])
    
# 3. Check what offices 333 and 334 are
    print("\nChecking offices 333 and 334 in distribution:")
    for r in dist:
        if r.get("cod_oficina") in [333, 334, "333", "334"]:
            print(r)

# 4. Check if there are cached sales for yesterday (2026-06-17)
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT cache_key, last_updated FROM sales_cache")
    keys = cursor.fetchall()
    print("\nSales Cache Keys:")
    for k in keys:
        if "2026-06-17" in k[0]:
            print(k)
    conn.close()
