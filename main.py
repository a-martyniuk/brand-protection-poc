import asyncio
import os
from scrapers.meli_scraper import MeliScraper
from logic.policy_engine import PolicyEngine
from logic.supabase_handler import SupabaseHandler

async def run_pipeline(search_urls):
    # 1. Initialize Handlers
    print("Starting Brand Protection Pipeline...")
    try:
        db = SupabaseHandler()
    except Exception as e:
        print(f"Database initialization failed: {e}")
        print("Continuing with local data only...")
        db = None

    # 2. Scrape Data
    scraper = MeliScraper(search_urls)
    raw_products = await scraper.scrape()
    
    # 3. Save Raw Data (Backup)
    scraper.save_results()

    if not db:
        print("Skipping database sync and policy engine as Supabase is not configured.")
        return

    # Deduplicate local products by meli_id before upserting
    # Whitelist updated to include DNA and Media columns
    DB_COLUMNS_WHITELIST = ["meli_id", "title", "price", "url", "seller_name", "seller_location", "thumbnail"]
    
    unique_products = {}
    for p in raw_products:
        mid = p["id"]
        if mid not in unique_products:
            unique_products[mid] = {k: v for k, v in {
                "meli_id": mid,
                "title": p["title"],
                "price": p["price"],
                "url": p["url"],
                "seller_name": p.get("seller_name"),
                "seller_location": p.get("seller_location"),
                "thumbnail": p.get("thumbnail")
            }.items() if k in DB_COLUMNS_WHITELIST}
    
    db_ready_products = list(unique_products.values())
    print(f"Syncing {len(db_ready_products)} unique products to Supabase (including DNA & Media)...")
    
    upserted_data = db.upsert_products(db_ready_products)
    if not upserted_data:
        print("Failed to sync products to Supabase.")
        return

    # 5. Fetch Policies & Detect Violations
    policies = db.get_policies()
    if not policies:
        print("No policies found in database. Please define them via the Supabase dashboard.")
        # For PoC, let's insert a dummy policy if none exist? 
        # Better to wait for user to set them.
        return

    engine = PolicyEngine(policies)
    
    # Match upserted UUIDs back to our products for the violation log
    meli_to_uuid = {p["meli_id"]: p["id"] for p in upserted_data}
    
    violations_to_insert = []
    for p in db_ready_products:
        p["uuid"] = meli_to_uuid.get(p["meli_id"])
        product_violations = engine.evaluate_product(p)
        for v in product_violations:
            v["product_id"] = p["uuid"]
            violations_to_insert.append(v)

    if violations_to_insert:
        print(f"Detected {len(violations_to_insert)} violations! Logging to DB...")
        db.log_violation(violations_to_insert)
    else:
        print("No violations detected in this run.")

if __name__ == "__main__":
    # Example starting URLs for Nutricia Bagó products
    TARGET_URLS = [
        "https://listado.mercadolibre.com.ar/nutricia-bago",
        "https://listado.mercadolibre.com.ar/leche-nutrilon",
        "https://listado.mercadolibre.com.ar/leche-vital"
    ]
    asyncio.run(run_pipeline(TARGET_URLS))
