import sqlite3
import json

conn = sqlite3.connect('uploads/cache.db')
cursor = conn.cursor()

# Get products catalog
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key='catalog_productos'")
catalog_row = cursor.fetchone()
products_by_code = {}
if catalog_row:
    for p in json.loads(catalog_row[0]):
        products_by_code[str(p["Cod_Producto"])] = p

# Let's get today's sales from cache (updated at 8:32)
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key LIKE '2026-06-09%'")
sales_data = json.loads(cursor.fetchone()[0])

TABLA_TO_PRODUCT_NAME = {
    'SIGT_CHANCES':              'CHANCE',
    'SIGT_CHANCES_RASPA':        'RASPITA',
    'SIGT_DOBLE_GANA':           'DOBLE CHANCE',
    'SIGT_SUPER_ASTRO':          'SUPER ASTRO',
    'SIGT_BALOTO':               'BALOTO',
    'SIGT_RECARGAS':             'RECARGA EN LINEA',
    'SIGT_SG_GIROS_CREADOS':     'GIROS',
    'SIGT_LOTERIAS_LINEA':       'LOTERIA EN LINEA',
    'SIGT_RECAUDOS_EMPRESAS':    'RECAUDOS EMPRESARIALES',
    'SIGT_VENTA_INCENTIVO_COBRO':'TRANSACCIONES CNB',
}

COD_TO_PRODUCT_NAME = {
    5: 'SUPER ASTRO',
    22005: 'TRANSACCIONES CNB',
    22069: 'RASPITA',
    22059: 'BALOTO',
    22070: 'MILOTO',
    22075: 'COLOR LOTO',
}

def resolve_product_name_old(sale):
    cod_prod = sale.get("Cod_Producto")
    if cod_prod is not None:
        try:
            cod_prod_int = int(cod_prod)
            if cod_prod_int in COD_TO_PRODUCT_NAME:
                return COD_TO_PRODUCT_NAME[cod_prod_int]
        except:
            pass
            
    src_table = sale.get("Tabla_Origen")
    if src_table and src_table in TABLA_TO_PRODUCT_NAME:
        return TABLA_TO_PRODUCT_NAME[src_table]
            
    return "OTROS"

# New logic
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
        
    return "OTROS"

def resolve_product_name_new(sale):
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
            return normalize_product(prod_type or prod_name)
            
        code_map = {
            22059: "BALOTO",
            22070: "MILOTO",
            22075: "COLOR LOTO",
            22069: "RASPITA",
            5: "SUPER ASTRO",
            22005: "TRANSACCIONES CNB",
            17287: "BET PLAY",
            17288: "BET PLAY",
            21931: "BET PLAY",
            21972: "BET PLAY"
        }
        try:
            cod_prod_int = int(cod_prod)
            if cod_prod_int in code_map:
                return code_map[cod_prod_int]
        except:
            pass
            
    src_table = sale.get("Tabla_Origen")
    if src_table and src_table in TABLA_TO_PRODUCT_NAME:
        return TABLA_TO_PRODUCT_NAME[src_table]
            
    return "OTROS"

old_totals = {}
new_totals = {}

for s in sales_data:
    # Exclude payouts etc.
    src_table = s.get("Tabla_Origen")
    s_code = s.get("Cod_Producto")
    if src_table in {'SIGT_SG_GIROS_PAGADOS', 'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
        continue
    if src_table == 'SIGT_RECAUDOS_MAESTRO' and str(s_code) != '22005':
        continue
        
    val = float(s.get("Venta_Neta") or 0.0)
    
    p_old = resolve_product_name_old(s)
    p_new = resolve_product_name_new(s)
    
    old_totals[p_old] = old_totals.get(p_old, 0.0) + val
    new_totals[p_new] = new_totals.get(p_new, 0.0) + val

print(f"{'PRODUCT':<25} | {'OLD TOTAL':<15} | {'NEW TOTAL':<15}")
print("-" * 60)
all_products = sorted(list(set(old_totals.keys()) | set(new_totals.keys())))
for p in all_products:
    print(f"{p:<25} | ${old_totals.get(p, 0.0):>13,.2f} | ${new_totals.get(p, 0.0):>13,.2f}")

conn.close()
