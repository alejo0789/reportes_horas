import sqlite3
import json

conn = sqlite3.connect('uploads/cache.db')
cursor = conn.cursor()

# Get the cache data for today
cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key LIKE '2026-06-11%'")
row = cursor.fetchone()
if row:
    sales = json.loads(row[0])
    
    # Load product catalog to map product codes to product types/names
    cursor.execute("SELECT data_json FROM sales_cache WHERE cache_key='catalog_productos'")
    cat_row = cursor.fetchone()
    products_by_code = {}
    if cat_row:
        for p in json.loads(cat_row[0]):
            products_by_code[p["Cod_Producto"]] = p

    # Normalization helper (matching backend logic)
    def normalize_product(name):
        if not name:
            return "OTROS"
        name = name.upper()
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

    total_sales = 0.0
    by_product = {}
    for s in sales:
        cod_prod = s.get("Cod_Producto")
        p_info = products_by_code.get(cod_prod)
        if p_info:
            p_type = p_info.get("Tipo_Producto") or p_info.get("Tipo Producto")
            p_name = p_info.get("Producto")
            norm = normalize_product(p_type or p_name)
        else:
            norm = "OTROS"
            
        val = float(s.get("Venta_Neta", 0.0))
        by_product[norm] = by_product.get(norm, 0.0) + val
        
        # Exclude count-based
        if norm not in {"GIROS", "TRANSACCIONES CNB", "RECAUDOS EMPRESARIALES"}:
            total_sales += val
            
    print("Breakdown of monetary products:")
    for prod, val in sorted(by_product.items(), key=lambda x: -x[1]):
        print(f"  {prod}: ${val:,.2f}")
    print(f"\nTotal sales excluding count-based: ${total_sales:,.2f}")
else:
    print("No cache found.")

conn.close()
