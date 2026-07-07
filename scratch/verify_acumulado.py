"""
Verifica de forma INDEPENDIENTE el "acumulado del mes" (venta_mes, meta_parcial,
meta_full y %) que muestra el reporte de WhatsApp, y ademas lo desglosa POR
PROMOTOR usando el cruce cod_oficina de distribution.json.

Fuentes (las mismas que usa el backend, leidas por separado):
  - uploads/goals.json          -> meta por sitio/oficina/producto/fecha
  - uploads/distribution.json   -> cod_oficina -> promotor / impulsador / zona
  - cache.db catalog_sitios     -> Cod_Sitio -> Cod_Oficina
  - cache.db catalog_productos  -> Cod_Producto -> producto (para resolve_product_name)
  - cache.db "AAAA-MM-01..hoy"  -> ventas del mes (la misma fila que consume el reporte)

Reutiliza resolve_product_name del backend para clasificar cada venta igual que
en produccion (no se re-implementa la logica de normalizacion).

Uso:
    python scratch/verify_acumulado.py                 # nacional, todos los productos
    python scratch/verify_acumulado.py --producto BALOTO
    python scratch/verify_acumulado.py --promotor "Hamer Medina"
    python scratch/verify_acumulado.py --por-promotor  # desglose de cada promotor
    python scratch/verify_acumulado.py --hasta 2026-07-07
"""
import os
import sys
import json
import argparse
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)  # raiz del proyecto: main.py usa imports 'from backend.xxx'

from backend.cache import get_cached_sales  # noqa: E402
import backend.main as backend  # noqa: E402  (carga goals_store/distribution en import)

COUNT_BASED = {"RECAUDOS EMPRESARIALES", "GIROS", "TRANSACCIONES CNB"}
SKIP_TABLES = {"SIGT_PAGOS", "SIGT_PAGOGEN_MAESTRO"}

ap = argparse.ArgumentParser()
ap.add_argument("--hasta", default=date.today().isoformat(), help="YYYY-MM-DD (default hoy)")
ap.add_argument("--producto", default=None, help="Filtrar un producto")
ap.add_argument("--promotor", default=None, help="Filtrar oficinas de un promotor")
ap.add_argument("--por-promotor", action="store_true", help="Desglose por promotor")
args = ap.parse_args()

hasta_date = args.hasta
month = hasta_date[:7]
month_start = f"{month}-01 00:00:00"
hasta_key = f"{hasta_date} 23:59:59"
sales_key = f"{month_start}_{hasta_key}"

# --- catalogos ---
sites_data, _ = get_cached_sales("catalog_sitios")
site_to_office = {}
if sites_data:
    for s in sites_data:
        sc, oc = s.get("Cod_Sitio"), s.get("Cod_Oficina")
        if sc is not None and oc is not None:
            site_to_office[int(sc)] = int(oc)
site_to_office[333033] = 333
site_to_office[334034] = 334

products_data, _ = get_cached_sales("catalog_productos")
products_by_code = {}
if products_data:
    for p in products_data:
        cp = p.get("Cod_Producto")
        if cp is not None:
            products_by_code[str(cp)] = p

# --- distribution: cod_oficina -> promotor ---
office_promoter = {}
for d in backend.distribution_store or []:
    oc = d.get("cod_oficina")
    if oc is not None:
        office_promoter[int(oc)] = (d.get("promotor") or "").strip()

# oficinas objetivo segun filtro de promotor
if args.promotor:
    target = args.promotor.strip().lower()
    target_offices = {oc for oc, pr in office_promoter.items() if pr.lower() == target}
    if not target_offices:
        print(f"⚠️  No hay oficinas para promotor '{args.promotor}'. Nombres disponibles (muestra):")
        for pr in sorted(set(office_promoter.values()))[:20]:
            print("   -", pr)
        sys.exit(1)
else:
    target_offices = set(office_promoter.keys())  # nacional

# --- ventas del mes ---
sales_data, updated = get_cached_sales(sales_key)
if sales_data is None:
    print(f"❌ No existe la fila de cache de ventas '{sales_key}'.")
    print("   Abre el reporte del mes en el dashboard/whatsapp para poblarla y reintenta.")
    sys.exit(1)

# venta_mes[producto][promotor]
venta = {}
for sale in sales_data:
    if sale.get("Tabla_Origen") in SKIP_TABLES:
        continue
    sc = sale.get("Cod_Sitio")
    if sc is None:
        continue
    try:
        oc = site_to_office.get(int(sc))
    except Exception:
        continue
    if oc is None or oc not in target_offices:
        continue
    pname = backend.resolve_product_name(sale, products_by_code)
    pr = office_promoter.get(oc, "(sin promotor)")
    venta.setdefault(pname, {}).setdefault(pr, 0.0)
    venta[pname][pr] += float(sale.get("Venta_Neta") or 0.0)

# --- metas del mes ---
meta_parcial = {}
meta_full = {}
for prod_name, recs in (backend.goals_store or {}).items():
    if recs and not recs[0].get("activo", True):
        continue
    for r in recs:
        f = str(r.get("fecha", ""))
        if not f.startswith(month):
            continue
        oc = r.get("cod_oficina")
        if oc is None:
            continue
        oc = int(oc)
        if oc not in target_offices:
            continue
        val = float(r.get("meta") or 0.0)
        if prod_name in COUNT_BASED:
            val = float(round(val))
        pr = office_promoter.get(oc, "(sin promotor)")
        meta_full.setdefault(prod_name, {}).setdefault(pr, 0.0)
        meta_full[prod_name][pr] += val
        if f <= hasta_date:
            meta_parcial.setdefault(prod_name, {}).setdefault(pr, 0.0)
            meta_parcial[prod_name][pr] += val


def pct(v, m):
    return (v / m * 100.0) if m > 0 else (100.0 if v > 0 else 0.0)


def sum_over(d, prod, promoters=None):
    inner = d.get(prod, {})
    if promoters is None:
        return sum(inner.values())
    return sum(inner.get(p, 0.0) for p in promoters)


products = sorted(set(list(venta.keys()) + list(meta_parcial.keys()) + list(meta_full.keys())))
if args.producto:
    products = [p for p in products if p.upper() == args.producto.upper()]

scope = args.promotor if args.promotor else "NACIONAL (todas las oficinas)"
print("=" * 64)
print(f"VERIFICACION ACUMULADO DEL MES  |  {month}  hasta {hasta_date}")
print(f"Ambito: {scope}   |   Ventas cache actualizado: {updated}")
print(f"Oficinas en el ambito: {len(target_offices)}")
print("=" * 64)

for prod in products:
    v = sum_over(venta, prod)
    mp = sum_over(meta_parcial, prod)
    mf = sum_over(meta_full, prod)
    pref = "" if prod in COUNT_BASED else "$"
    print(f"\n📦 {prod}")
    print(f"   Venta mes         : {pref}{round(v):,}")
    print(f"   Meta parcial(hoy) : {pref}{round(mp):,}   -> Parcial {pct(v,mp):.1f}%")
    print(f"   Meta full (mes)   : {pref}{round(mf):,}   -> Mensual {pct(v,mf):.1f}%")
    if args.por_promotor:
        proms = sorted(set(list(venta.get(prod,{}).keys()) + list(meta_parcial.get(prod,{}).keys())))
        for pr in proms:
            vv = venta.get(prod,{}).get(pr,0.0)
            mm = meta_parcial.get(prod,{}).get(pr,0.0)
            print(f"      - {pr:<28} venta {pref}{round(vv):>12,}  meta {pref}{round(mm):>12,}  = {pct(vv,mm):5.1f}%")

print("\n" + "=" * 64)
print("Compara 'Parcial' con la linea '↳ Parcial (mes a hoy)' del reporte.")
