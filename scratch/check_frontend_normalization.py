import sqlite3
import json
import os

DB_PATH = "uploads/cache.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_productos'")
productos_data = json.loads(cursor.fetchone()[0])

products_by_code = {}
for p in productos_data:
    cod = p.get("Cod_Producto")
    if cod is not None:
        products_by_code[str(cod)] = p

cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key LIKE '2026-06-24%'")
row = cursor.fetchone()

SPECIAL_PRODUCTS = [
    { "key": "BET PLAY", "patterns": ["BETPLAY", "BET PLAY", "BTP"] },
    { "key": "PATA MILLONARIA", "patterns": ["PATA MILLONARIA", "PT"] },
    { "key": "DOBLE CHANCE", "patterns": ["3C DOBLE CH REGIONAL", "4C DOBLE CH REGIONAL", "DOBLE CHANCE", "DOBLE GANA", "DOBLE CH", "DDCH"] },
    { "key": "BILLONARIO NACIONAL", "patterns": ["BILLONARIO", "BILLONARIO NACIONAL"] },
    { "key": "CHANCE MILLONARIO", "patterns": ["CHANCE MILLONARIO", "CHML"] },
    { "key": "COLOR LOTO", "patterns": ["COLOR LOTO", "CLOT"] },
    { "key": "MILOTO", "patterns": ["MILOTO", "MLT"] },
    { "key": "BALOTO", "patterns": ["BALOTO", "BLT", "BLL"] },
    { "key": "LOTERIA EN LINEA", "patterns": ["LOTERIA EN LINEA", "LOT", "LOTE", "RYL"] },
    { "key": "GIROS", "patterns": ["GIROS", "GIRO", "ENVIO GIRO"] }
]

def get_special_product_key(product_name):
    if not product_name:
        return None
    name = str(product_name).strip().replace("*", "").upper()
    for spec in SPECIAL_PRODUCTS:
        for pat in spec["patterns"]:
            if pat in name or name == pat:
                return spec["key"]
    return None

def normalize_product(raw_name):
    if not raw_name:
        return "OTROS"
    name = str(raw_name).strip().replace("*", "").upper()
    
    spec_key = get_special_product_key(name)
    if spec_key:
        return spec_key
        
    if name.startswith("CHON") or name.startswith("CHOD") or name.startswith("BOGO") or name.startswith("CHO"):
        return "CHANCE"
    if "CHANCE" in name or name == "CH":
        return "CHANCE"
    if "SUPER ASTRO" in name or "ASTRO" in name or name == "SA":
        return "SUPER ASTRO"
    if "GIROS" in name or name == "GIROS":
        return "GIROS"
    if "RECARGA" in name or name == "RC":
        return "RECARGA EN LINEA"
    if "TRANSACCIONES CNB" in name or "CNB" in name or name == "TRCNB":
        return "TRANSACCIONES CNB"
    if "RECAUDOS EMPRESARIALES" in name or "RECAUDOS" in name or name == "RCDEM":
        return "RECAUDOS EMPRESARIALES"
    if "LOTERIAS" in name or "LOTERIA" in name or name == "LOT":
        return "LOTERIA EN LINEA"
    if "RASPAS" in name or "RASPA" in name or name == "RASPITA" or name == "RYL":
        return "RASPITA"
    if "BALOTO" in name or name == "BALOTO":
        return "BALOTO"
    if "MILOTO" in name or name == "MILOTO":
        return "MILOTO"
    if "COLOR LOTO" in name or name == "COLORLOTO":
        return "COLOR LOTO"
    if "PATA MILLONARIA" in name or name == "PATA":
        return "PATA MILLONARIA"
        
    return name

if row:
    data = json.loads(row[0])
    
    loteria_sales = [item for item in data if item.get("Tabla_Origen") == 'SIGT_LOTERIAS_LINEA']
    
    # Categorize them!
    sums_by_norm = {}
    
    for s in loteria_sales:
        normProd = None
        cod_prod = str(s.get("Cod_Producto"))
        if cod_prod in products_by_code:
            prod = products_by_code[cod_prod]
            prodName = prod.get("Producto")
            prodType = prod.get("Tipo_Producto") or prod.get("Tipo Producto")
            specKey = get_special_product_key(prodName)
            if specKey:
                normProd = specKey
            else:
                normProd = normalize_product(prodType or prodName)
        else:
            normProd = "LOTERIA EN LINEA" # Fallback from frontend logic
            
        val = float(s.get("Venta_Neta", 0) or 0)
        sums_by_norm[normProd] = sums_by_norm.get(normProd, 0) + val

    print("\n--- SUMS FOR TABLE SIGT_LOTERIAS_LINEA BY FRONTEND NORMALIZED NAME ---")
    for k, v in sums_by_norm.items():
        print(f"{k}: {v}")
        
    # Also sum by HOUR to see what the hours look like
    sums_by_hour = {}
    for s in loteria_sales:
        hour = s.get("Hora", "00:00:00")
        val = float(s.get("Venta_Neta", 0) or 0)
        sums_by_hour[hour] = sums_by_hour.get(hour, 0) + val
    
    print("\n--- SUMS FOR LOTERIA BY HOUR ---")
    for h, v in sorted(sums_by_hour.items()):
        print(f"{h}: {v}")

conn.close()
