
import asyncio
from logic.supabase_handler import SupabaseHandler
from logic.identification_engine import IdentificationEngine

async def fix_levels():
    print("🔄 Fixing Match Levels...")
    db = SupabaseHandler()
    engine = IdentificationEngine()
    
    # 1. Fetch identified listings
    res = db.supabase.table("compliance_audit").select("listing_id").gt("match_level", 0).execute()
    listing_ids = [r["listing_id"] for r in res.data]
    print(f"Found {len(listing_ids)} identified items to re-check.")
    
    # 2. Re-identify in chunks
    for i in range(0, len(listing_ids), 100):
        chunk_ids = listing_ids[i:i+100]
        # Fetch listing data
        l_res = db.supabase.table("meli_listings").select("*").in_("id", chunk_ids).execute()
        listings = l_res.data
        
        updates = []
        for l in listings:
            audit = engine.identify_product(l)
            updates.append({
                "listing_id": l["id"],
                "match_level": audit["match_level"],
                "master_product_id": audit["master_product_id"],
                "violation_details": audit["violation_details"]
            })
            
        if updates:
            print(f"Updating batch {i//100 + 1}...")
            # Use upsert via log_compliance_audit logic
            db.log_compliance_audit(updates)
            
    print("✅ Match levels updated.")

if __name__ == "__main__":
    asyncio.run(fix_levels())
