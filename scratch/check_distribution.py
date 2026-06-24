import json
import os

path = r"c:\Users\alejandro.carvajal\Documents\reportes_ventas\ventasxhora\uploads\distribution.json"
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    zones = set()
    for item in data:
        z = item.get("zona")
        if z:
            zones.add(z.strip())
    print("Zonas en distribution:")
    for z in sorted(list(zones)):
        print(f" - {z}")
except Exception as e:
    print(e)
