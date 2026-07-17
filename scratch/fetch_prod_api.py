import urllib.request
import json

url = "http://192.168.2.91:8032/api/ventas?desde=2026-06-24%2000:00:00&hasta=2026-06-24%2023:59:59&force_refresh=true"
print(f"Fetching: {url}")
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
        sales = data.get("data", [])
        print(f"Total sales records: {len(sales)}")
        
        loteria_total = 0
        loteria_records = 0
        for s in sales:
            if s.get("Tabla_Origen") == "SIGT_LOTERIAS_LINEA":
                val = float(s.get("Venta_Neta") or 0)
                loteria_total += val
                loteria_records += 1
                
        print(f"Total Loteria: {loteria_total} from {loteria_records} records")
except Exception as e:
    print(f"Error fetching: {e}")
