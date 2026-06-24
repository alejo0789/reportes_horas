import sqlite3
import pandas as pd
import os

db_path = "uploads/cache.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, zone, role FROM whatsapp_coordinators")
    coors = cursor.fetchall()
    print("Coordinators in SQLite:")
    for c in coors:
        print(c)
    conn.close()

# Let's inspect Dist. Promotores 2026.xlsx if it exists
excel_path = "Dist. Promotores 2026.xlsx"
if os.path.exists(excel_path):
    df = pd.read_excel(excel_path)
    print("\nColumns in Excel:", df.columns.tolist())
    if "Zona" in df.columns:
        print("\nUnique Zonas in Excel:")
        print(df["Zona"].dropna().unique().tolist())
    
    # Let's see unique zones and their count of offices/sites
    print("\nUnique Zonas and row counts in Excel:")
    print(df["Zona"].value_counts())
