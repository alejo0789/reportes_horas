import urllib.request
import json

try:
    response = urllib.request.urlopen("http://127.0.0.1:8032/api/whatsapp-coordinators")
    data = response.read().decode('utf-8')
    coors = json.loads(data)
    print("Coordinators from running server:")
    for c in coors:
        if "YUDY" in c["name"]:
            print(c)
except Exception as e:
    print(f"FAILED: {e}")
