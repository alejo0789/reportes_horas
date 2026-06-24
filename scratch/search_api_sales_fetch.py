with open("frontend/app.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "/api/sales" in line or "fetch" in line:
        print(f"Line {i+1}: {line.strip()}")
