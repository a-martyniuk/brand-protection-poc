import asyncio
import os
from scrapers.meli_api_scraper import MeliAPIScraper
from logic.identification_engine import IdentificationEngine
from logic.supabase_handler import SupabaseHandler

async def run_pipeline():
    print("Starting Advanced Brand Protection Pipeline (4-Layer Mode)...")
    
    # 1. Initialize Handlers
    db = SupabaseHandler()
    engine = IdentificationEngine()
    
    # 2. Fetch Master Products
    master_products = db.get_master_products()
    if not master_products:
        print("Master catalog is empty. Run migration first.")
        return
        
    brands = list(set([mp["brand"] for mp in master_products if mp.get("brand")]))
    print(f"Loaded {len(master_products)} products across brands: {brands}")

    # 3. Scrape Meli Listings (Full Catalog Coverage)
    print(f"\n🚀 Expanding search to all {len(brands)} catalog brands...")
    search_items = []
    for brand in brands:
        search_items.append({
            "product_name": brand,
            "official_id": None
        })

    scraper = MeliAPIScraper(search_items)
    raw_listings = await scraper.scrape()
    scraper.save_results() # Save to user_data/raw_listings.json
    
    # 4. Sync Listings to DB
    print(f"Syncing {len(raw_listings)} listings to 'meli_listings'...")
    unique_listings = {} # Deduplicate by meli_id
    for l in raw_listings:
        mid = l["meli_id"]
        if mid == "N/A": continue
        if mid not in unique_listings:
            unique_listings[mid] = {
                "meli_id": mid,
                "title": l["title"],
                "price": l.get("price", 0),
                "url": l.get("url"),
                "seller_name": l.get("seller_name"),
                "seller_location": l.get("seller_location", "N/A"),
                "thumbnail": l.get("thumbnail"),
                "category": l.get("category"),
                "brand_detected": l.get("brand_detected"),
                "seller_id": l.get("seller_id"),
                "is_official_store": l.get("is_official_store", False),
                "official_store_id": l.get("official_store_id"),
                "seller_reputation": l.get("seller_reputation", {}),
                "attributes": l.get("attributes", {}),
                "available_quantity": l.get("available_quantity", 0)
            }
    
    listings_to_sync = list(unique_listings.values())
    upserted_listings = db.upsert_meli_listings(listings_to_sync)
    if not upserted_listings:
        print("Failed to sync listings. Aborting audit.")
        return

    # 5. Identification & Compliance Audit (Initial Fast Pass)
    print("\n⚡ Running Initial Identification & Compliance Audit...")
    audit_records = []
    
    # Reload listings from DB in chunks (Supabase .in_ limit is ~1000)
    batch_size = 1000
    all_enriched = []
    for i in range(0, len(listings_to_sync), batch_size):
        batch_ids = [l["meli_id"] for l in listings_to_sync[i:i+batch_size]]
        response = db.supabase.table("meli_listings").select("*").in_("meli_id", batch_ids).execute()
        all_enriched.extend(response.data)

    # Map meli_id -> listing_uuid
    meli_to_uuid = {l["meli_id"]: l["id"] for l in all_enriched}
    
    # Run Identification & Audit
    for l in all_enriched:
        audit = engine.identify_product(l)
        fraud_score = audit["fraud_score"]
        risk_level = engine.get_risk_level(fraud_score)
        
        audit_records.append({
            "listing_id": meli_to_uuid[l["meli_id"]],
            "master_product_id": audit["master_product_id"],
            "match_level": audit["match_level"],
            "is_brand_correct": audit["is_brand_correct"],
            "is_price_ok": audit["is_price_ok"],
            "is_publishable_ok": audit["is_publishable_ok"],
            "fraud_score": fraud_score,
            "risk_level": risk_level,
            "violation_details": audit["violation_details"]
        })

    if audit_records:
        print(f"Logging {len(audit_records)} initial audit results to Supabase...")
        db.log_compliance_audit(audit_records)
    else:
        print("No audit records generated.")

    # 6. Background Enrichment (Automated Deep Scraping ONLY on matched products)
    print("\n🔍 Checking for matched listings that need deep enrichment...")
    from enrichers.product_enricher import ProductEnricher
    # Using serial mode (batch=1, delay=random 8-63s) for stealth
    enricher = ProductEnricher(batch_size=1)
    
    # Scale to 10,000 items as requested
    await enricher.enrich_products(limit=10000) 
    
    # 7. Final Re-Audit (Only for enriched items to update scores)
    print("\n🔄 Running Final Audit to incorporate enriched data...")
    # Refresh all active audit records to make sure UI is up to date
    import subprocess
    import sys
    subprocess.run([sys.executable, "refresh_audit.py"])
    print("Pipeline execution complete.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
