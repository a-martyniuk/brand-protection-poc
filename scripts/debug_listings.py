import asyncio
import os
import sys
import json

# Add project root to path
sys.path.append(os.getcwd())

from logic.supabase_handler import SupabaseHandler

async def inspect_listings():
    db = SupabaseHandler()
    print("Checking first 10 listings with 'N/A' seller names...")
    
    # We look for meli_id like the ones in the screenshot
    res = db.supabase.table("meli_listings").select("*").in_("meli_id", ["MLA1517652477", "MLA873925327"]).execute()
    data = res.data
    
    if not data:
        print("No matches for these IDs found.")
        return
        
    for i, l in enumerate(data):
        print(f"\n--- Listing {i+1}: {l['meli_id']} ---")
        print(f"Title: {l['title'][:50]}")
        print(f"Seller In DB: {l['seller_name']}")
        
        attrs = l.get("attributes", {})
        print("Attributes Keys:", list(attrs.keys()))
        
        meta_seller = attrs.get("meta_seller_name")
        meta_sold = attrs.get("meta_sold_quantity")
        ean = l.get("ean_published")
        print(f"Enriched Seller: {meta_seller}")
        print(f"Sold Quantity: {meta_sold}")
        print(f"EAN: {ean}")

if __name__ == "__main__":
    asyncio.run(inspect_listings())
