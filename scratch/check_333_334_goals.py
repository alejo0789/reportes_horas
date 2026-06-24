import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOALS_FILE = os.path.join(BASE_DIR, "uploads", "goals.json")

with open(GOALS_FILE, "r", encoding="utf-8") as f:
    goals = json.load(f)

# Find all records for 333 or 334
records_333_334 = []
for prod, recs in goals.items():
    for r in recs:
        if r.get("cod_oficina") in [333, 334, "333", "334"]:
            r["producto_excel"] = prod
            records_333_334.append(r)

print(f"Total 333/334 records in goals: {len(records_333_334)}")

# Find distinct values for keys
keys = ["cod_sitio", "sitio_venta", "cod_oficina", "producto_excel"]
for k in keys:
    distinct_vals = set(r.get(k) for r in records_333_334)
    print(f"Distinct values for '{k}': {distinct_vals}")

# Let's print some sample records with non-zero goals
non_zero_recs = [r for r in records_333_334 if float(r.get("meta") or 0.0) > 0]
print(f"\nNon-zero meta records count: {len(non_zero_recs)}")
print("Sample non-zero records (up to 10):")
for r in non_zero_recs[:10]:
    print(r)
