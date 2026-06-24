import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_FILE = os.path.join(BASE_DIR, "backend", "main.py")

with open(MAIN_FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if "backend.cache" in line or "find_active_" in line:
        print(f"Line {i}: {line.strip()}")
