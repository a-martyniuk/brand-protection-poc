
import asyncio
from logic.supabase_handler import SupabaseHandler
from logic.identification_engine import IdentificationEngine

async def global_reaudit():
    print("🔄 Starting Global Re-Audit (Brand Detection Base)...")
    db = SupabaseHandler()
    engine = IdentificationEngine()
    
    # 1. Fetch ALL active/non-discarded listings
    res = db.supabase.table("meli_listings").select("id", count="exact").execute()
    total = res.count
    print(f"Loaded {total} total listings to re-evaluate.")
    
    # 2. Re-identify in chunks of 500
    for i in range(0, total, 500):
        l_res = db.supabase.table("meli_listings").select("*").offset(i).limit(500).execute()
        listings = l_res.data
        
        updates = []
        for l in listings:
            audit = engine.identify_product(l)
            # We update EVERY record with its new match_level (Exacta, Alta, KW, or Noise)
            updates.append({
                "listing_id": l["id"],
                "match_level": audit["match_level"],
                "master_product_id": audit["master_product_id"],
                "violation_details": audit["violation_details"],
                "fraud_score": audit["fraud_score"],
                "risk_level": audit["risk_level"],
                "is_price_ok": audit["is_price_ok"],
                "is_brand_correct": audit["is_brand_correct"],
                "is_publishable_ok": audit["is_publishable_ok"]
            })
            
        if updates:
            print(f"Syncing batch {(i//500) + 1}...")
            db.log_compliance_audit(updates)
            
    print("✅ Global re-audit complete. Labels and noise-reduction are now live.")

if __name__ == "__main__":
    asyncio.run(global_reaudit())
