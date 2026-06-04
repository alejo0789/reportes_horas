import os
import openpyxl
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger("excel_parser")

def detect_product_from_filename(filename: str) -> str:
    fn = filename.upper()
    if "BTP" in fn or "BETPLAY" in fn or "BET PLAY" in fn:
        return "BET PLAY"
    if "RYL" in fn or "RASPA" in fn:
        return "RASPITA"
    if "CHML" in fn or "CHANCE MILLONARIO" in fn:
        return "CHANCE MILLONARIO"
    if "CLOT" in fn or "COLOR" in fn:
        return "COLOR LOTO"
    if "DDCH" in fn or "DOBLE" in fn:
        return "DOBLE CHANCE"
    if "BLL" in fn or "BILLONARIO" in fn:
        return "BILLONARIO NACIONAL"
    if "BLT" in fn or "BALOTO" in fn:
        return "BALOTO"
    if "MLT" in fn or "MILOTO" in fn:
        return "MILOTO"
    if "PT" in fn or "PATA" in fn:
        return "PATA MILLONARIA"
    if "GIROS" in fn:
        return "GIROS"
    if "RCDEM" in fn or "RECAUDOS" in fn:
        return "RECAUDOS EMPRESARIALES"
    if "TRCNB" in fn or "CNB" in fn:
        return "TRANSACCIONES CNB"
    if "RC" in fn or "RECARGA" in fn:
        return "RECARGA EN LINEA"
    if "LOT" in fn or "LOTERIA" in fn:
        return "LOTERIA EN LINEA"
    if "SA" in fn or "ASTRO" in fn:
        return "SUPER ASTRO"
    if "CH" in fn or "CHANCE" in fn:
        return "CHANCE"
    return None

def parse_metas_excel(file_path):
    """
    Parses a goals excel file.
    Structure:
      Row 1: Dates at columns 12, 15, 18, 21, etc. (1-indexed: Col L, O, R, U...)
      Row 2: Product Name at Col 12, 15, etc.
      Row 3: Header names: Cod. Zona, Zona, Cod. Ciudad, Ciudad, Cod. Oficina, Oficina, Cod. Sitio, Sitio de venta, Estado, Fecha Creacion, Producto
      Row 4+: Data rows.
    """
    filename = os.path.basename(file_path)
    filename_product = detect_product_from_filename(filename)

    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active

    # 1. Read first 3 rows to identify the date columns and the product
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 4:
        raise ValueError("Excel file has too few rows to be a valid Metas sheet.")

    row1 = rows[0]
    row2 = rows[1]
    row3 = rows[2]

    # Find the day groups starting at Col 12 (index 11)
    day_columns = []
    col_idx = 11
    while col_idx < len(row1):
        date_val = row1[col_idx]
        if date_val is not None:
            # Check if it's a date or datetime
            if isinstance(date_val, datetime):
                date_str = date_val.strftime("%Y-%m-%d")
            elif isinstance(date_val, str):
                # Try to parse string date
                try:
                    dt = pd.to_datetime(date_val)
                    date_str = dt.strftime("%Y-%m-%d")
                except:
                    date_str = date_val
            else:
                date_str = str(date_val)
            
            # The product is listed in row 2 (index 1) at this column or row 3 (index 2)
            product_name = row2[col_idx]
            if not product_name or str(product_name).strip().upper() in ["", "UNKNOWN", "NONE"]:
                product_name = filename_product or "UNKNOWN"
            
            day_columns.append({
                "col_idx": col_idx,
                "date": date_str,
                "product_name": filename_product or str(product_name).strip()
            })
        col_idx += 3

    logger.info(f"Found {len(day_columns)} day columns in metas file.")

    # 2. Iterate data rows
    records = []
    # Row 3 (index 2) should contain 'Cod. Sitio' around index 6
    # Let's inspect column positions dynamically just in case
    headers = [str(h).strip().lower() if h is not None else "" for h in row3]
    
    try:
        idx_cod_sitio = next(i for i, h in enumerate(headers) if "cod. sitio" in h or "cod_sitio" in h)
    except StopIteration:
        # Fallback to index 6
        idx_cod_sitio = 6

    try:
        idx_sitio = next(i for i, h in enumerate(headers) if "sitio de venta" in h or "sitio_venta" in h)
    except StopIteration:
        idx_sitio = 7

    try:
        idx_oficina = next(i for i, h in enumerate(headers) if "cod. oficina" in h or "cod_oficina" in h)
    except StopIteration:
        idx_oficina = 4

    try:
        idx_producto = next(i for i, h in enumerate(headers) if "producto" in h and "tipo" not in h)
    except StopIteration:
        idx_producto = 10

    # Read rows from Row 4 onwards
    for r_idx in range(3, len(rows)):
        row = rows[r_idx]
        if not row or len(row) <= idx_cod_sitio:
            continue
            
        cod_sitio = row[idx_cod_sitio]
        # Ignore empty rows, totals, or header repetitions
        if cod_sitio is None or str(cod_sitio).strip().lower() in ["", "total", "totales", "cod. sitio"]:
            continue
            
        try:
            cod_sitio_int = int(cod_sitio)
        except ValueError:
            # Not a numeric site code, skip
            continue

        oficina_cod = row[idx_oficina]
        sitio_nom = row[idx_sitio]
        prod_id = row[idx_producto]

        # Extract goals for each day
        for day in day_columns:
            c_idx = day["col_idx"]
            if c_idx >= len(row):
                continue
                
            meta_val = row[c_idx]
            part_val = row[c_idx + 1] if c_idx + 1 < len(row) else 0
            venta_val = row[c_idx + 2] if c_idx + 2 < len(row) else 0

            # Convert to numeric
            meta = float(meta_val) if meta_val is not None else 0.0
            part = float(part_val) if part_val is not None else 0.0
            venta = float(venta_val) if venta_val is not None else 0.0

            records.append({
                "cod_sitio": cod_sitio_int,
                "sitio_venta": sitio_nom,
                "cod_oficina": int(oficina_cod) if oficina_cod is not None else None,
                "producto_id": int(prod_id) if prod_id is not None else None,
                "producto_excel": day["product_name"],
                "fecha": day["date"],
                "meta": meta,
                "participacion": part,
                "venta_excel": venta
            })

    return records

def parse_promoters_excel(file_path):
    """
    Parses the promoters distribution file.
    Expected columns: Cod. Oficina, Oficina, Coordinador comercial, Promotor, Zona, Municipio, Impulsador de productos, Embajadora Betplay, email
    """
    df = pd.read_excel(file_path, sheet_name="Distribucion comercial")
    
    # Standardize column names
    df.columns = [str(c).strip() for c in df.columns]
    
    # We want to match: Cod. Oficina, Promotor, Coordinador comercial, Zona
    # Let's map them to reliable keys
    rename_map = {
        "Cod. Oficina": "cod_oficina",
        "Oficina": "oficina",
        "Coordinador comercial": "coordinador",
        "Promotor": "promotor",
        "Zona": "zona",
        "Municipio": "municipio",
        "Impulsador  de productos": "impulsador",
        "Embajadora Betplay": "embajadora",
        "email": "email"
    }
    
    # Find matching columns
    active_rename = {}
    for col in df.columns:
        for original, standard in rename_map.items():
            if col.lower().replace("  ", " ") == original.lower().replace("  ", " "):
                active_rename[col] = standard
                break
                
    df = df.rename(columns=active_rename)
    
    # Filter rows with empty office codes or headers
    if "cod_oficina" in df.columns:
        df = df[df["cod_oficina"].notna()]
        df = df[df["cod_oficina"].apply(lambda x: str(x).strip().isdigit() or isinstance(x, (int, float)))]
        df["cod_oficina"] = df["cod_oficina"].astype(int)
        
    df = df.fillna("")
    return df.to_dict(orient="records")
