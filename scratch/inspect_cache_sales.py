import sqlite3
import json
import os

db_path = "uploads/cache.db"
if not os.path.exists(db_path):
    print("uploads/cache.db not found")
    sys.exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get the cached sales for June 11, 2026
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key LIKE '2026-06-11%'")
row = cursor.fetchone()
if not row:
    print("No cached sales for today")
    conn.close()
    sys.exit(0)
    
sales = json.loads(row[0])

# Get the catalog
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key='catalog_productos'")
cat_row = cursor.fetchone()
products_by_code = {}
if cat_row:
    for p in json.loads(cat_row[0]):
        products_by_code[str(p.get("Cod. Producto") or p.get("Cod_Producto"))] = p

# Normalize and resolve matching backend logic
def get_special_product_key(name):
    if not name:
        return None
    name = name.upper()
    if "BETPLAY" in name or "BET PLAY" in name or name == "BTP":
        return "BET PLAY"
    if "PATA MILLONARIA" in name or name == "PT":
        return "PATA MILLONARIA"
    if any(pat in name for pat in ["3C DOBLE CH REGIONAL", "4C DOBLE CH REGIONAL", "DOBLE CHANCE", "DOBLE GANA", "DOBLE CH", "DDCH"]):
        return "DOBLE CHANCE"
    return None

def normalize_product(name):
    if not name:
        return "OTROS"
    name = name.upper()
    if "CHANCE MILLONARIO" in name:
        return "CHANCE MILLONARIO"
    if "CHANCE" in name or name == "CH":
        return "CHANCE"
    if "ASTRO" in name or name == "AST":
        return "SUPER ASTRO"
    if "BALOTO" in name or name == "BALOTO":
        return "BALOTO"
    if "BETPLAY" in name or "BET PLAY" in name or name == "BTP":
        return "BET PLAY"
    if "RECARGAS" in name or "RECARGA" in name or name == "REC":
        return "RECARGA EN LINEA"
    if "GIROS" in name or "GIRO" in name:
        return "GIROS"
    if "CNB" in name or name == "CNB" or "CORRESPONSAL" in name:
        return "TRANSACCIONES CNB"
    if "RECAUDOS" in name or "RECAUDO" in name:
        return "RECAUDOS EMPRESARIALES"
    return "OTROS"

def resolve_product_name(sale, products_by_code):
    cod_prod = sale.get("Cod_Producto")
    if cod_prod is not None:
        cod_prod_str = str(cod_prod)
        if products_by_code and cod_prod_str in products_by_code:
            prod_info = products_by_code[cod_prod_str]
            prod_name = prod_info.get("Producto")
            prod_type = prod_info.get("Tipo_Producto") or prod_info.get("Tipo Producto")
            spec_key = get_special_product_key(prod_name)
            if spec_key:
                return spec_key
            return normalize_product(prod_type or prod_name)
    return "OTROS"

by_product = {}
total_excl = 0.0

for s in sales:
    # Applying the payout exclusions
    src_table = s.get("Tabla_Origen")
    if src_table in {'SIGT_PAGOS', 'SIGT_PAGOGEN_MAESTRO'}:
        continue
        
    p_name = resolve_product_name(s, products_by_code)
    val = float(s.get("Venta_Neta") or 0.0)
    
    by_product[p_name] = by_product.get(p_name, 0.0) + val
    if p_name not in {"GIROS", "TRANSACCIONES CNB", "RECAUDOS EMPRESARIALES"}:
        total_excl += val

print("--- Cache Sales by Resolved Product ---")
for p, v in sorted(by_product.items(), key=lambda x: -x[1]):
    print(f"  {p:<25}: ${v:,.2f}")
    
print(f"\nTotal excluding count-based: ${total_excl:,.2f}")

conn.close()
