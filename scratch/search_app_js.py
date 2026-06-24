with open("frontend/app.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "isCountBased" in line or "is_count_based" in line or "GIROS" in line:
        print(f"Line {i+1}: {line.strip()}")
