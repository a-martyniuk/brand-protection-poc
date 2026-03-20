import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from logic.supabase_handler import SupabaseHandler

async def audit_enrichment():
    db = SupabaseHandler()
    print("--- Enriched Data Audit ---")
    
    # 1. Total listings
    res_total = db.supabase.table("meli_listings").select("id", count="exact").execute()
    total = res_total.count
    
    # 2. Listings with EAN
    res_ean = db.supabase.table("meli_listings").select("id", count="exact").not_.is_("ean_published", "null").not_.eq("ean_published", "").execute()
    ean_count = res_ean.count
    
    # 3. Listings with Seller Name (not N/A)
    res_seller = db.supabase.table("meli_listings").select("id", count="exact").not_.eq("seller_name", "N/A").execute()
    seller_count = res_seller.count
    
    # 4. Listings with Sold Quantity > 0
    res_sold = db.supabase.table("meli_listings").select("id", count="exact").gt("sold_quantity", 0).execute()
    sold_count = res_sold.count
    
    # 5. Listings with Official Store = True
    res_official = db.supabase.table("meli_listings").select("id", count="exact").eq("is_official_store", True).execute()
    official_count = res_official.count

    print(f"Total Listings: {total}")
    print(f"Listings with EAN: {ean_count}")
    print(f"Listings with Correct Seller: {seller_count}")
    print(f"Listings with Sales (>0): {sold_count}")
    print(f"Official Stores: {official_count}")

    if ean_count > 0:
        print("\nSample EANs found:")
        res_sample = db.supabase.table("meli_listings").select("meli_id, ean_published").not_.is_("ean_published", "null").not_.eq("ean_published", "").limit(5).execute()
        for r in res_sample.data:
            print(f"  {r['meli_id']}: {r['ean_published']}")

if __name__ == "__main__":
    asyncio.run(audit_enrichment())
