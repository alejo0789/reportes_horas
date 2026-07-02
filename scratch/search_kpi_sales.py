with open("frontend/app.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "kpiSales" in line or "Venta Neta del Día" in line or "kpi-sales" in line:
        print(f"Line {i+1}: {line.strip()}")
