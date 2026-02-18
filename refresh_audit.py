import asyncio
from logic.supabase_handler import SupabaseHandler
from logic.identification_engine import IdentificationEngine

async def refresh_audit():
    print("🔄 Starting Audit Refresh...")
    db = SupabaseHandler()
    engine = IdentificationEngine()
    
    # 1. Fetch all listings from DB (handling pagination for > 1000 rows)
    print("Fetching active listings from 'meli_listings' in batches...")
    listings = []
    batch_size = 1000
    offset = 0
    
    while True:
        res = db.supabase.table("meli_listings").select("*").range(offset, offset + batch_size - 1).execute()
        batch = res.data
        listings.extend(batch)
        print(f"Loaded {len(listings)} listings...")
        if len(batch) < batch_size:
            break
        offset += batch_size
    
    print(f"Total listings loaded: {len(listings)}")
    
    # 2. Re-run identification for each
    print("Re-calculating fraud scores with new Multipack & Unit Price logic...")
    audit_records = []
    for l in listings:
        # identify_product expects the listing structure from the scraper
        # which is largely what's in the DB, but we ensure 'attributes' is handled
        audit = engine.identify_product(l)
        
        audit_records.append({
            "listing_id": l["id"],
            "master_product_id": audit["master_product_id"],
            "match_level": audit["match_level"],
            "is_brand_correct": audit["is_brand_correct"],
            "is_price_ok": audit["is_price_ok"],
            "is_publishable_ok": audit["is_publishable_ok"],
            "fraud_score": audit["fraud_score"],
            "risk_level": engine.get_risk_level(audit["fraud_score"]),
            "violation_details": audit["violation_details"]
        })
    
    # 3. Batch Update Audit Table
    if audit_records:
        print(f"Syncing {len(audit_records)} updated audit results to Supabase...")
        # log_compliance_audit uses upsert, so it will update existing records for these listings
        db.log_compliance_audit(audit_records)
        print("✅ Audit refresh complete. New scores are now live in the Dashboard.")
    else:
        print("No listings found to audit.")

if __name__ == "__main__":
    asyncio.run(refresh_audit())
