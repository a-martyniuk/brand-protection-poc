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

    # 3. Scrape Meli Listings
    # For PoC, focus on top brands
    poc_brands = [b for b in brands if "Nutrilon" in b or "Vital" in b]
    search_items = []
    for brand in poc_brands:
        search_items.append({
            "product_name": brand,
            "official_id": None # No specific ID for brand search
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
                "price": l["price"],
                "url": l["url"],
                "seller_name": l["seller_name"],
                "seller_location": l["seller_location"],
                "thumbnail": l["thumbnail"],
                "category": l.get("category"),
                "brand_detected": l.get("brand_detected")
            }
    
    listings_to_sync = list(unique_listings.values())
    upserted_listings = db.upsert_meli_listings(listings_to_sync)
    if not upserted_listings:
        print("Failed to sync listings. Aborting audit.")
        return

    # Map meli_id -> listing_uuid
    meli_to_uuid = {l["meli_id"]: l["id"] for l in upserted_listings}

    # 5. Identification & Compliance Audit
    print("Running Identification & Compliance Audit...")
    audit_records = []
    
    for l in raw_listings:
        if l["meli_id"] not in meli_to_uuid: continue
        
        listing_uuid = meli_to_uuid[l["meli_id"]]
        
        # Run Identification
        master_id, match_level, fraud_score = engine.identify_product(l)
        risk_level = engine.get_risk_level(fraud_score)
        
        # Compliance Checks
        is_brand_correct = True
        is_price_ok = True
        is_publishable_ok = True
        violation_details = {}

        if master_id:
            # Fetch master context for this match
            mp = next((item for item in master_products if item["id"] == master_id), None)
            if mp:
                # 1. Brand Correction
                if l.get("brand_detected") and l["brand_detected"].lower() != mp["brand"].lower():
                    is_brand_correct = False
                    violation_details["brand_mismatch"] = {"expected": mp["brand"], "found": l["brand_detected"]}
                
                # 2. Price Check
                if mp.get("list_price") and l["price"] < mp["list_price"]:
                    is_price_ok = False
                    violation_details["low_price"] = {"min": mp["list_price"], "actual": l["price"]}
                
                # 3. Publishable Check
                if not mp.get("is_publishable", True):
                    is_publishable_ok = False
                    violation_details["restricted_sku"] = True

        audit_records.append({
            "listing_id": listing_uuid,
            "master_product_id": master_id,
            "match_level": match_level,
            "is_brand_correct": is_brand_correct,
            "is_price_ok": is_price_ok,
            "is_publishable_ok": is_publishable_ok,
            "fraud_score": fraud_score,
            "risk_level": risk_level,
            "violation_details": violation_details
        })

    if audit_records:
        print(f"Logging {len(audit_records)} audit results to Supabase...")
        db.log_compliance_audit(audit_records)
        print("Pipeline execution complete.")
    else:
        print("No audit records generated.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
