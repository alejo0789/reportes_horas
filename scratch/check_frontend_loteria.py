import json
import sqlite3
import sys
import os

sys.path.insert(0, os.getcwd())

conn = sqlite3.connect('uploads/cache.db')
cursor = conn.cursor()

# We copy the frontend ProductNormalizer rules
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
        
    if "LOTERIAS" in name or "LOTERIA" in name or name == "LOT":
        return "LOTERIA EN LINEA"
        
    return "OTROS"

TABLA_TO_PRODUCT_NAME = {
    'SIGT_LOTERIAS_LINEA':       'LOTERIA EN LINEA',
}

cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key='catalog_productos'")
catalog_row = cursor.fetchone()
products_by_code = {}
if catalog_row:
    for p in json.loads(catalog_row[0]):
        products_by_code[str(p["Cod_Producto"])] = p

def resolve_product_name(sale):
    cod_prod = sale.get("Cod_Producto")
    if cod_prod is not None:
        cod_prod_str = str(cod_prod)
        if cod_prod_str in products_by_code:
            p = products_by_code[cod_prod_str]
            prod_name = p.get("Producto")
            prod_type = p.get("Tipo_Producto") or p.get("Tipo Producto")
            spec_key = get_special_product_key(prod_name)
            if spec_key:
                return spec_key
            
            if prod_type:
                res = normalize_product(prod_type)
                if res != "OTROS": return res
            if prod_name:
                res = normalize_product(prod_name)
                if res != "OTROS": return res
    src_table = sale.get("Tabla_Origen")
    if src_table and src_table in TABLA_TO_PRODUCT_NAME:
        return TABLA_TO_PRODUCT_NAME[src_table]
    return "OTROS"

cursor.execute("SELECT cache_key FROM sales_cache WHERE cache_key LIKE '2026-06-24%'")
keys = cursor.fetchall()
if keys:
    key = keys[0][0]
    cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key=?", (key,))
    sales_data = json.loads(cursor.fetchone()[0])
    
    total = 0
    total_table_only = 0
    for s in sales_data:
        src_table = s.get("Tabla_Origen")
        s_code = s.get("Cod_Producto")
        
        prod = resolve_product_name(s)
        val = float(s.get("Venta_Neta") or 0.0)
        
        if prod == "LOTERIA EN LINEA":
            total += val
        
        if src_table == 'SIGT_LOTERIAS_LINEA':
            total_table_only += val
            
    print(f"Total resolved as LOTERIA EN LINEA: {total}")
    print(f"Total pure SIGT_LOTERIAS_LINEA table: {total_table_only}")

conn.close()
