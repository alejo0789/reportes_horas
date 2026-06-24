with open("backend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "TABLA_TO_PRODUCT_NAME" in line or "tabla_to_product_name" in line:
        print(f"Line {i+1}: {line.strip()}")
