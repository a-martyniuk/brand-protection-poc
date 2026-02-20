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
                "attributes": l.get("attributes", {})
            }
    
    listings_to_sync = list(unique_listings.values())
    upserted_listings = db.upsert_meli_listings(listings_to_sync)
    if not upserted_listings:
        print("Failed to sync listings. Aborting audit.")
        return

    # 5. Background Enrichment (NEW: Automated Deep Scraping)
    print("\n🔍 Checking for listings that need deep enrichment...")
    from enrichers.product_enricher import ProductEnricher
    enricher = ProductEnricher(batch_size=10, delay_between_requests=2)
    
    # We only enrich products that were just scraped/updated and missing data
    # For PoC speed, we limit this to a small number or only those from this run
    # For now, let's run it for the products we just synced that lack EAN
    await enricher.enrich_products(limit=50) 
    
    # Reload listings from DB to get enriched data (EAN, brand, attributes)
    print("Reloading enriched listings from database...")
    enriched_response = db.supabase.table("meli_listings").select("*").in_("meli_id", [l["meli_id"] for l in listings_to_sync]).execute()
    raw_listings_enriched = enriched_response.data

    # Map meli_id -> listing_uuid
    meli_to_uuid = {l["meli_id"]: l["id"] for l in raw_listings_enriched}

    # 6. Identification & Compliance Audit
    print("Running Identification & Compliance Audit...")
    audit_records = []
    
    # Use unique_listings values instead of raw_listings to avoid duplicate audit records
    for l in unique_listings.values():
        if l["meli_id"] not in meli_to_uuid: continue
        
        listing_uuid = meli_to_uuid[l["meli_id"]]
        
        # Run Identification & Audit
        audit = engine.identify_product(l)
        fraud_score = audit["fraud_score"]
        risk_level = engine.get_risk_level(fraud_score)
        
        audit_records.append({
            "listing_id": listing_uuid,
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
        print(f"Logging {len(audit_records)} audit results to Supabase...")
        db.log_compliance_audit(audit_records)
        print("Pipeline execution complete.")
    else:
        print("No audit records generated.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
