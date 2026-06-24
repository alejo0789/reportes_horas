with open("backend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def resolve_product_name" in line:
        print(f"Line {i+1}: {line.strip()}")
        # print next 30 lines
        for j in range(i+1, min(i+31, len(lines))):
            print(f"Line {j+1}: {lines[j].strip()}")
