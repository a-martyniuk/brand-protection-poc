import pandas as pd
import os

file_path = 'BPP master data skus.xlsx'
try:
    df = pd.read_excel(file_path)
    print("Columns:")
    for col in df.columns:
        print(f"- {col}")
    print("\nFirst row:")
    print(df.iloc[0].to_dict())
    print("\nTypes:")
    print(df.dtypes)
except Exception as e:
    print(f"Error reading excel: {e}")
