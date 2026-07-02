import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(BASE_DIR, "frontend", "app.js")

with open(APP_JS, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines in app.js: {len(lines)}")
for i, line in enumerate(lines, 1):
    if "coordinatorsListBody" in line or "elements =" in line or "const elements" in line:
        print(f"Line {i}: {line.strip()}")
