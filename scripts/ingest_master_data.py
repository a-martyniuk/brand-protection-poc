import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def clean_boolean(val):
    if pd.isna(val):
        return False
    return str(val).strip().upper() == 'SI'

def clean_decimal(val):
    if pd.isna(val):
        return None
    try:
        if isinstance(val, str):
             # Remove $ and dots, replace comma with dot
            val = val.replace('$', '').replace('.', '').replace(',', '.')
        return float(val)
    except:
        return None

def ingest_data(file_path):
    print(f"Reading {file_path}...")
    df = pd.read_excel(file_path)

    # Normalize column names for easier access if needed, but we'll specific mapping
    records = []
    
    print("Processing rows...")
    for _, row in df.iterrows():
        try:
            record = {
                "sap_code": int(row['SAP CODE']) if pd.notna(row['SAP CODE']) else None,
                "ean": str(int(row['EAN'])) if pd.notna(row['EAN']) else None, # preserve integer formatting
                "product_name": row['Unificador'] if pd.notna(row['Unificador']) else None,
                "distributor": row['R. Social comercializadora'] if pd.notna(row['R. Social comercializadora']) else None,
                "business_unit": row['BU'] if pd.notna(row['BU']) else None,
                "therapeutic_area": row['TA'] if pd.notna(row['TA']) else None,
                "brand": row['Marca'] if pd.notna(row['Marca']) else None,
                "stage": row['Etapa'] if pd.notna(row['Etapa']) else None,
                "substance": row['Sustancia'] if pd.notna(row['Sustancia']) else None,
                "format": row['Formato'] if pd.notna(row['Formato']) else None,
                "fc_dry": clean_decimal(row['FC (Dry)']),
                "fc_net": clean_decimal(row['FC (Net)']),
                "status": row['Estado'] if pd.notna(row['Estado']) else None,
                "is_publishable": row['Publicable si o no'] == 'SI',
                "list_price": clean_decimal(row['PVP minimo/lista']),
                "discount_allowed": row['Descuento si o no'] == 'SI',
                "units_per_pack": int(row['Unidad por Presentación']) if pd.notna(row['Unidad por Presentación']) else 1
            }
            records.append(record)
        except Exception as e:
            print(f"Skipping row due to error: {e}")
            continue

    print(f"Prepared {len(records)} records for insertion/upsert.")
    
    # Batch insert to avoid timeouts
    batch_size = 100
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            # We use upsert if 'sap_code' was unique, but for now we just insert. 
            # Ideally we should clear the table first or upsert based on ID. 
            # Since we don't have a clear unique key constraint on the DB side for SAP/EAN yet (schema didn't enforce it),
            # we will just INSERT.
            data, count = supabase.table('official_products').insert(batch).execute()
            print(f"Inserted batch {i // batch_size + 1}")
        except Exception as e:
            print(f"Error inserting batch: {e}")

if __name__ == "__main__":
    file_path = "BPP master data skus.xlsx"
    if os.path.exists(file_path):
        ingest_data(file_path)
    else:
        print(f"File not found: {file_path}")
