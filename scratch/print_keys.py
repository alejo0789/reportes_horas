import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALES_FILE = os.path.join(BASE_DIR, "scratch", "yesterday_sales.json")

with open(SALES_FILE, "r") as f:
    sales = json.load(f)

# Find first record where Tabla_Origen is SIGT_CHANCES
chance_rec = next((s for s in sales if s.get("Tabla_Origen") == "SIGT_CHANCES"), None)
print("Chance record keys and values:")
print(chance_rec)
