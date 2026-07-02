import json
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "uploads", "cache.db")
DIST_FILE = os.path.join(BASE_DIR, "uploads", "distribution.json")
SALES_FILE = os.path.join(BASE_DIR, "scratch", "yesterday_sales.json")
PRODUCTS_FILE = os.path.join(BASE_DIR, "scratch", "catalog_productos.json")

# Load yesterday's sales
with open(SALES_FILE, "r") as f:
    sales = json.load(f)

# Load catalog_sitios from cache.db
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_sitios'")
sitios_data = json.loads(cursor.fetchone()[0])

cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key = 'catalog_productos'")
productos_data = json.loads(cursor.fetchone()[0])
conn.close()

# Build maps
site_to_office = {}
office_to_name = {}
for s in sitios_data:
    s_code = s.get("Cod_Sitio")
    off_code = s.get("Cod_Oficina")
    off_name = s.get("Oficina")
    if s_code is not None and off_code is not None:
        site_to_office[int(s_code)] = int(off_code)
        office_to_name[int(off_code)] = off_name

products_by_code = {}
for p in productos_data:
    cod = p.get("Cod_Producto")
    if cod is not None:
        products_by_code[str(cod)] = p

# Normalize function from main.py
def get_special_product_key(product_name):
    if not product_name:
        return None
    name = str(product_name).strip().replace("*", "").upper()
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

def resolve_product_name(sale):
    TABLA_TO_PRODUCT_NAME = {
        'SIGT_CHANCES':              'CHANCE',
        'SIGT_CHANCES_RASPA':        'RASPITA',
        'SIGT_DOBLE_GANA':           'DOBLE CHANCE',
        'SIGT_SUPER_ASTRO':          'SUPER ASTRO',
        'SIGT_BALOTO':               'BALOTO',
        'SIGT_RECARGAS':             'RECARGA EN LINEA',
        'SIGT_SG_GIROS_CREADOS':     'GIROS',
        'SIGT_SG_GIROS_PAGADOS':     'GIROS',
        'SIGT_LOTERIAS_LINEA':       'LOTERIA EN LINEA',
        'SIGT_RECAUDOS_EMPRESAS':    'RECAUDOS EMPRESARIALES',
        'SIGT_VENTA_INCENTIVO_COBRO':'TRANSACCIONES CNB',
    }
    cod_prod = sale.get("Cod_Producto")
    if cod_prod is not None:
        cod_prod_str = str(cod_prod)
        if cod_prod_str in products_by_code:
            prod_info = products_by_code[cod_prod_str]
            prod_name = prod_info.get("Producto")
            prod_type = prod_info.get("Tipo_Producto") or prod_info.get("Tipo Producto")
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

# Analyze sales for Rodrigo's offices: 134, 136, 138, 167
rodrigo_offices = {134, 136, 138, 167}

rodrigo_sales_by_office = {off: {} for off in rodrigo_offices}
rodrigo_sales_total = {}
unmapped_sites = set()

# Also let's keep track of sales for offices 333 and 334
owo_sales_by_office = {333: {}, 334: {}}

for s in sales:
    # Exclude non-sales
    src_table = s.get("Tabla_Origen")
    if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
        continue
        
    site_code = s.get("Cod_Sitio")
    if site_code is None:
        continue
        
    site_code = int(site_code)
    office_code = site_to_office.get(site_code)
    
    if office_code is None:
        unmapped_sites.add(site_code)
        continue
        
    val = float(s.get("Venta_Neta") or 0.0)
    prod = resolve_product_name(s)
    
    if office_code in rodrigo_offices:
        # Save by office
        rodrigo_sales_by_office[office_code][prod] = rodrigo_sales_by_office[office_code].get(prod, 0.0) + val
        # Save total
        rodrigo_sales_total[prod] = rodrigo_sales_total.get(prod, 0.0) + val
        
    if office_code in [333, 334]:
        owo_sales_by_office[office_code][prod] = owo_sales_by_office[office_code].get(prod, 0.0) + val

print("\n--- SALES BREAKDOWN FOR RODRIGO LEDEZMA (OFFICES 134, 136, 138, 167) ---")
for prod, total in sorted(rodrigo_sales_total.items()):
    print(f"{prod}: ${total:,.2f}")
print(f"TOTAL RODRIGO SALES: ${sum(rodrigo_sales_total.values()):,.2f}")

print("\n--- SALES BREAKDOWN BY OFFICE FOR RODRIGO ---")
for off, prods in sorted(rodrigo_sales_by_office.items()):
    off_name = office_to_name.get(off, f"Oficina {off}")
    print(f"\nOffice {off} ({off_name}):")
    for prod, total in sorted(prods.items()):
        print(f"  {prod}: ${total:,.2f}")
    print(f"  Total Office: ${sum(prods.values()):,.2f}")

print("\n--- SALES BREAKDOWN FOR OFFICES 333 AND 334 (OWO) ---")
for off in [333, 334]:
    print(f"\nOffice {off} ({office_to_name.get(off, 'Unknown')}):")
    for prod, total in sorted(owo_sales_by_office[off].items()):
        print(f"  {prod}: ${total:,.2f}")
    print(f"  Total Office: ${sum(owo_sales_by_office[off].values()):,.2f}")

print(f"\nTotal unmapped sites: {len(unmapped_sites)}")
