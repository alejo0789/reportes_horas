import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES_CSS = os.path.join(BASE_DIR, "frontend", "styles.css")

with open(STYLES_CSS, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if "action-btn-primary" in line or "promoters-whatsapp-section" in line or "action-btn" in line:
        print(f"Line {i}: {line.strip()}")
