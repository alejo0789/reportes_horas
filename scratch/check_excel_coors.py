import pandas as pd
import os

excel_path = "Dist. Promotores 2026.xlsx"
if os.path.exists(excel_path):
    df = pd.read_excel(excel_path)
    # Print the unique combinations of Coordinator and Zone
    print("Combinations of Coordinator and Zone in Excel:")
    unique_combos = df[['Coordinador comercial', 'Zona']].drop_duplicates()
    print(unique_combos)
