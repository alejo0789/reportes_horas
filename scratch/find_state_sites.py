import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(BASE_DIR, "frontend", "app.js")

with open(APP_JS, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if "State.sites" in line:
        print(f"Line {i}: {line.strip()}")
