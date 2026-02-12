import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def check_schema():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    try:
        # Get one record to check columns
        res = supabase.table("master_products").select("*").limit(1).execute()
        if res.data:
            print("Columns found in master_products:", res.data[0].keys())
        else:
            print("No data in master_products to check columns.")
            
        # Try to insert a dummy to see if it fails
        # res = supabase.table("master_products").upsert({"ean": "test_ean", "discount_allowed": True}).execute()
    except Exception as e:
        print(f"Error checking schema: {e}")

if __name__ == "__main__":
    check_schema()
