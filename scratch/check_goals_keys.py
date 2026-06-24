import json
import os

goals_file = "uploads/goals.json"
if os.path.exists(goals_file):
    with open(goals_file, "r", encoding="utf-8") as f:
        goals = json.load(f)
    print("Goal keys (products):")
    for k in goals.keys():
        print(f"  {k}: {len(goals[k])} records")
else:
    print("goals.json not found")
