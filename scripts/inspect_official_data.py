from logic.supabase_handler import SupabaseHandler
import json

def inspect():
    db = SupabaseHandler()
    official = db.get_official_products()
    print(f"Total Official Products: {len(official)}")
    # Print first 5 to see structure
    for p in official[:10]:
        print(f"ID: {p['id']}, Name: {p['product_name']}, Brand: {p['brand']}, Price: {p['list_price']}")

if __name__ == "__main__":
    inspect()
