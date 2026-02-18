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

profutura_items = [
    {
        "ean": "7791905001607",
        "product_name": "Nutrilon Profutura 1 x 800g",
        "brand": "Nutrilon",
        "stage": "1",
        "fc_net": 0.8,
        "list_price": 45000,
        "is_publishable": True,
        "units_per_pack": 1,
        "status": "ACTIVO",
        "business_unit": "ELN",
        "therapeutic_area": "Maternizados"
    },
    {
        "ean": "7791905001614",
        "product_name": "Nutrilon Profutura 2 x 800g",
        "brand": "Nutrilon",
        "stage": "2",
        "fc_net": 0.8,
        "list_price": 42000,
        "is_publishable": True,
        "units_per_pack": 1,
        "status": "ACTIVO",
        "business_unit": "ELN",
        "therapeutic_area": "Maternizados"
    },
    {
        "ean": "7791905001621",
        "product_name": "Nutrilon Profutura 3 x 800g",
        "brand": "Nutrilon",
        "stage": "3",
        "fc_net": 0.8,
        "list_price": 38000,
        "is_publishable": True,
        "units_per_pack": 1,
        "status": "ACTIVO",
        "business_unit": "ELN",
        "therapeutic_area": "Maternizados"
    },
    {
        "ean": "7791905001638",
        "product_name": "Nutrilon Profutura 4 x 800g",
        "brand": "Nutrilon",
        "stage": "4",
        "fc_net": 0.8,
        "list_price": 35000,
        "is_publishable": True,
        "units_per_pack": 1,
        "status": "ACTIVO",
        "business_unit": "ELN",
        "therapeutic_area": "Maternizados"
    }
]

def inject():
    print(f"Injecting {len(profutura_items)} Profutura products into master_products...")
    try:
        # Check existing columns to avoid errors
        sample = supabase.table('master_products').select("*").limit(1).execute()
        existing_cols = set(sample.data[0].keys()) if sample.data else set()
        
        filtered_items = []
        for item in profutura_items:
            filtered_item = {k: v for k, v in item.items() if k in existing_cols}
            filtered_items.append(filtered_item)

        res = supabase.table('master_products').upsert(filtered_items, on_conflict='ean').execute()
        print(f"Successfully upserted {len(filtered_items)} products.")
    except Exception as e:
        print(f"Error during injection: {e}")

if __name__ == "__main__":
    inject()
