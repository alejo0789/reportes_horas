with open("backend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "cursor.execute" in line or "cursor.description" in line or "fetchall" in line:
        print(f"Line {i+1}: {line.strip()}")
