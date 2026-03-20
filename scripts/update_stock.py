import json
import os
import re
import requests
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

def extract_meli_id(url):
    """Prioritize 'wid' (Listing ID) over Product ID."""
    wid_match = re.search(r'wid=MLA(\d+)', url)
    if wid_match:
        return f"MLA{wid_match.group(1)}"
    match = re.search(r'MLA-?(\d+)', url)
    if match:
        return f"MLA{match.group(1)}"
    return "N/A"

async def update_stock():
    input_file = "user_data/raw_listings.json"
    listings = []
    
    from logic.supabase_handler import SupabaseHandler
    db = SupabaseHandler()

    if os.path.exists(input_file) and os.path.getsize(input_file) > 10:
        print(f"Loading listings from local file {input_file}...")
        with open(input_file, "r", encoding="utf-8") as f:
            listings = json.load(f)
    else:
        print(f"Local file empty or missing. Fetching listings from Supabase...")
        listings = db.get_meli_listings()

    if not listings:
        print("Error: No listings found in local file or Supabase.")
        return

    print(f"Found {len(listings)} listings. Processing IDs and fetching stock...")
    
    unique_items = {}
    for l in listings:
        # Prioritize extraction from URL (for wid/Listing ID) over DB ID (often Product ID)
        extracted_id = extract_meli_id(l.get("url", ""))
        meli_id = extracted_id if extracted_id != "N/A" else l.get("meli_id")
        
        if meli_id and meli_id != "N/A":
            l["meli_id"] = meli_id
            unique_items[meli_id] = l

    token = os.getenv("MELI_ACCESS_TOKEN")
    item_ids = list(unique_items.keys())
    batch_size = 20
    
    updated_count = 0
    forbidden_count = 0
    not_found_count = 0
    other_error_count = 0
    
    for i in range(0, len(item_ids), batch_size):
        batch = item_ids[i:i + batch_size]
        print(f"  Batch {i//batch_size + 1}/{(len(item_ids)-1)//batch_size + 1}...", end=" ")
        
        ids_str = ",".join(batch)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        try:
            url = f"https://api.mercadolibre.com/items?ids={ids_str}"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                results = response.json()
                codes = {}
                for res in results:
                    code = res.get("code")
                    codes[code] = codes.get(code, 0) + 1
                    
                    if code == 200:
                        body = res.get("body", {})
                        body_id = body.get("id")
                        stock = body.get("available_quantity", 0)
                        variations = body.get("variations", [])
                        if variations:
                            var_stock = sum(v.get("available_quantity", 0) for v in variations)
                            if var_stock > 0:
                                stock = var_stock
                        
                        for l in listings:
                            if l.get("meli_id") == body_id:
                                l["available_quantity"] = stock
                        updated_count += 1
                    elif code == 403:
                        forbidden_count += 1
                    elif code == 404:
                        not_found_count += 1
                    else:
                        other_error_count += 1
                print(f"Codes: {codes}")
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(0.3)

    # Sync back to Supabase
    print(f"\nSyncing {len(listings)} updated listings to Supabase...")
    db.upsert_meli_listings(listings)

    # Save to local file as backup
    os.makedirs("user_data", exist_ok=True)
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(listings, f, indent=4, ensure_ascii=False)

    print(f"\nUpdate Complete!")
    print(f"  Total IDs Processed: {len(item_ids)}")
    print(f"  Success (200): {updated_count}")
    print(f"  Forbidden (403): {forbidden_count}")
    print(f"  Not Found (404): {not_found_count}")
    print(f"  Others: {other_error_count}")


if __name__ == "__main__":
    asyncio.run(update_stock())
