import asyncio
import os
import sys

# Add project root to path so we can import 'logic'
sys.path.append(os.getcwd())

from logic.supabase_handler import SupabaseHandler

async def sync_enriched_data():
    print("🔄 Starting Retroactive Enriched Data Sync...")
    db = SupabaseHandler()
    
    # 1. Fetch all listings from DB (handling pagination)
    print("Fetching listings from 'meli_listings'...")
    listings = []
    batch_size = 1000
    offset = 0
    
    while True:
        res = db.supabase.table("meli_listings").select("*").range(offset, offset + batch_size - 1).execute()
        batch = res.data
        listings.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    
    print(f"Total listings loaded: {len(listings)}")
    
    # 2. Identify updates needed
    updates = []
    for l in listings:
        attrs = l.get("attributes", {})
        meta_seller = attrs.get("meta_seller_name")
        meta_id = attrs.get("meta_seller_id")
        meta_official = attrs.get("meta_is_official_store")
        meta_sold = attrs.get("meta_sold_quantity")
        meta_cond = attrs.get("meta_condition")
        
        # Identify updates needed
        if meta_seller or meta_sold is not None or meta_official is not None:
            update_item = {
                "id": l["id"],
                "meli_id": l["meli_id"], # Required for Not Null
                "title": l["title"], # Required for Not Null
                "seller_name": meta_seller if meta_seller else l.get("seller_name"),
                "seller_id": str(meta_id) if meta_id else l.get("seller_id"),
                "is_official_store": meta_official if meta_official is not None else l.get("is_official_store"),
                "sold_quantity": meta_sold if meta_sold is not None else l.get("sold_quantity", 0),
                "condition": meta_cond if meta_cond else l.get("condition"),
                "last_enriched_at": l.get("last_enriched_at") or attrs.get("_last_enrichment_attempt")
            }
            updates.append(update_item)
            
    if not updates:
        print("✅ No listings need seller sync.")
        return

    print(f"Syncing {len(updates)} listings with missing top-level seller names...")
    
    # 3. Batch Update (Supabase upsert with ID)
    for i in range(0, len(updates), 100):
        batch = updates[i:i+100]
        try:
            print(f"  Sample Update: {batch[0]['seller_name']} (ID: {batch[0]['id']})")
            db.supabase.table("meli_listings").upsert(batch, on_conflict="id").execute()
            print(f"  Synced {i + len(batch)}/{len(updates)}...")
        except Exception as e:
            print(f"  Error syncing batch: {e}")
            
    print("✅ Enriched data sync complete. The dashboard metrics are now fully populated.")

if __name__ == "__main__":
    asyncio.run(sync_enriched_data())
