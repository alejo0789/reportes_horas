import urllib.request
import json

try:
    response = urllib.request.urlopen("http://127.0.0.1:8032/api/whatsapp-administrators")
    data = response.read().decode('utf-8')
    print("SUCCESS: Endpoint responded!")
    print(json.loads(data))
except Exception as e:
    print(f"FAILED: {e}")
