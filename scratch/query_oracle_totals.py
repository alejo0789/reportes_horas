import sys
import os
sys.path.insert(0, os.getcwd())

from backend.db import db_manager
from backend.queries import VENTAS_POR_HORA_QUERY
import logging
import json

logging.basicConfig(level=logging.INFO)
db_manager.init_pools()

desde = "2026-06-09 00:00:00"
hasta = "2026-06-09 23:59:59"

results = []

# Query CAUCAMED
if db_manager.pool_cauca:
    try:
        with db_manager.get_cauca_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    row_dict["Fuente"] = "CAUCA"
                    results.append(row_dict)
                print(f"CAUCAMED returned {len(results)} rows.")
    except Exception as e:
        print(f"CAUCAMED query failed: {e}")

# Query FORTUMED
fortuna_count = 0
if db_manager.pool_fortuna:
    try:
        with db_manager.get_fortuna_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(VENTAS_POR_HORA_QUERY, {"desde": desde, "hasta": hasta})
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    row_dict["Fuente"] = "FORTUNA"
                    results.append(row_dict)
                    fortuna_count += 1
                print(f"FORTUMED returned {fortuna_count} rows.")
    except Exception as e:
        print(f"FORTUMED query failed: {e}")

# Mappings
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

# Fetch catalog products from cache to normalize
import sqlite3
sqlite_conn = sqlite3.connect('uploads/cache.db')
cursor = sqlite_conn.cursor()
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key='catalog_productos'")
catalog_row = cursor.fetchone()
products_by_code = {}
if catalog_row:
    for p in json.loads(catalog_row[0]):
        products_by_code[str(p["Cod_Producto"])] = p
sqlite_conn.close()

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
    src_table = sale.get("Tabla_Origen")
    if src_table and src_table in TABLA_TO_PRODUCT_NAME:
        return TABLA_TO_PRODUCT_NAME[src_table]
    return "OTROS"

product_totals = {}
for s in results:
    src_table = s.get("Tabla_Origen")
    s_code = s.get("Cod_Producto")
    if src_table in {'SIGT_SG_GIROS_PAGADOS', 'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
        continue
    if src_table == 'SIGT_RECAUDOS_MAESTRO' and str(s_code) != '22005':
        continue
        
    prod = resolve_product_name(s)
    val = float(s.get("Venta_Neta") or 0.0)
    product_totals[prod] = product_totals.get(prod, 0.0) + val

print("\nFRESH Oracle Totals by product:")
for prod, total in sorted(product_totals.items(), key=lambda x: -x[1]):
    print(f"  {prod}: ${total:,.2f}")

db_manager.close_pools()
