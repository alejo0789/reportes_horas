import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.excel_parser import parse_metas_excel, parse_promoters_excel

def test():
    print("Testing metas Excel (TRCNB)...")
    metas = parse_metas_excel("CIAL2/CIAL2/Asig Metas Mes Act TRCNB.xlsx")
    print(f"Loaded {len(metas)} metas records.")
    if metas:
        print("First record:", metas[0])
        
    print("\nTesting metas Excel (SA)...")
    metas_sa = parse_metas_excel("CIAL2/CIAL2/Asig Metas Mes Act SA.xlsx")
    print(f"Loaded {len(metas_sa)} metas records.")
    if metas_sa:
        print("First record:", metas_sa[0])

    print("\nTesting promoters Excel...")
    promoters = parse_promoters_excel("Dist. Promotores 2026.xlsx")
    print(f"Loaded {len(promoters)} promoters records.")
    if promoters:
        print("First record:", promoters[0])

if __name__ == "__main__":
    test()
