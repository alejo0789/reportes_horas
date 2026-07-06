"""
Muestra la respuesta de WhatsApp en el formato real del mensaje.

Consulta /api/whatsapp/query e imprime el campo `text` con los saltos
de linea reales (no el \\n escapado del JSON).

Uso:
    python scratch/render_whatsapp.py 573024226412 products
    python scratch/render_whatsapp.py 573024226412 offices
"""
import sys
import json
import urllib.request
import urllib.parse

BASE = "http://127.0.0.1:8032/api/whatsapp/query"

phone = sys.argv[1] if len(sys.argv) > 1 else "573024226412"
report_type = sys.argv[2] if len(sys.argv) > 2 else "products"
ref_date = sys.argv[3] if len(sys.argv) > 3 else None  # ej. 2026-07-05 para "ayer"

params = {"phone": phone, "report_type": report_type}
if ref_date:
    params["ref_date"] = ref_date
url = BASE + "?" + urllib.parse.urlencode(params)

with urllib.request.urlopen(url, timeout=120) as resp:
    data = json.loads(resp.read().decode("utf-8"))

print("=" * 50)
print(f"phone={phone}  report_type={report_type}")
print("=" * 50)
print(data.get("text", "(sin campo text)"))
print("=" * 50)
for k in ("sales", "goal", "compliance", "report_type"):
    if k in data:
        print(f"{k}: {data[k]}")
