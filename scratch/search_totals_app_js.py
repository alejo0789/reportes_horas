with open("frontend/app.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "totals." in line or "totalSales" in line or "salesTotal" in line:
        print(f"Line {i+1}: {line.strip()}")
