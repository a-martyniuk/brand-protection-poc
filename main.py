import asyncio
import os
from scrapers.meli_api_scraper import MeliAPIScraper
from logic.identification_engine import IdentificationEngine
from logic.supabase_handler import SupabaseHandler

async def run_pipeline():
    print("=" * 60)
    print("🚀 STARTING BRAND PROTECTION MASTER PIPELINE (MONTHLY MODE)")
    print("=" * 60)
    
    import subprocess
    import sys
    
    # 0. INITIALIZATION & CLEANUP
    db = SupabaseHandler()
    engine = IdentificationEngine()

    print("\n🧹 PHASE 0: Fresh Start (Clearing Previous Results)")
    db.clear_all_data() # Clears 'meli_listings' and 'compliance_audit'
    
    # Clear local temporary files/caches
    temp_files = ["user_data/raw_listings.json", "enricher_status.json", "data/raw_products.json", "tmp_products.txt"]
    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"  - Removed cache: {f}")
            except Exception as e:
                print(f"  - Could not remove {f}: {e}")

    # 1. INGEST MASTER DATA (Update Catalog from Excel)
    print("\n📦 PHASE 1: Ingesting Master Catalog from Excel...")
    subprocess.run([sys.executable, "scripts/ingest_master_data.py"])
    
    # 2. DISCOVERY (Scraping Meli Listings)
    print("\n🔍 PHASE 2: Discovering Listings (Super Discovery Mode)...")
    # Quick API Scraper (Based on Brand Names)
    master_products = db.get_master_products()
    if not master_products:
        print("Master catalog is empty. Ingestion failed?")
        return
        
    brands = list(set([mp["brand"] for mp in master_products if mp.get("brand")]))
    print(f"Loaded {len(master_products)} products across brands: {brands}")

    print(f"\n   [Discovery 1/2] API Keyword Scraper...")
    search_items = [{"product_name": b, "official_id": None} for b in brands]
    scraper = MeliAPIScraper(search_items)
    await scraper.scrape()
    scraper.save_results()
    
    print(f"\n   [Discovery 2/2] Browser Super-Discovery (Playwright)...")
    subprocess.run([sys.executable, "scripts/discover_listings.py", "--pages", "2"])
    
    # Syncing all discovered items to DB (already done within scrapers, but verified here)
    print("\n✅ Discovery phase complete.")

    # 3. INITIAL AUDIT (Identification)
    print("\n⚡ PHASE 3: Running Initial Identification & Compliance Audit...")
    subprocess.run([sys.executable, "refresh_audit.py"])

    # 4. ENRICHMENT PHASE 1 (Fast API)
    print("\n🚀 PHASE 4: Enrichment Level 1 (Official API - Fast Track)...")
    subprocess.run([sys.executable, "enrichers/meli_api_enricher.py", "500"]) 
    
    # 5. ENRICHMENT PHASE 2 (Deep Browser)
    print("\n🔍 PHASE 5: Enrichment Level 2 (Deep Scraper - Browser Mode)...")
    from enrichers.product_enricher import ProductEnricher
    # Serial mode (batch=1) for maximum stealth on deep data
    enricher = ProductEnricher(batch_size=1)
    await enricher.enrich_products(limit=1000) # Deep enrich a sample of matched items
    
    # 6. FINAL RE-AUDIT (Score Update)
    print("\n🔄 PHASE 6: Final Audit Refresh (Incorporating Enriched Data)...")
    subprocess.run([sys.executable, "refresh_audit.py"])
    
    # 7. FINAL NOISE PURGE
    print("\n🧹 PHASE 7: Final Noise Purge (Database Cleanup)...")
    subprocess.run([sys.executable, "cleanup_unrelated_noise.py"])

    print("\n" + "=" * 60)
    print("✅ MASTER PIPELINE EXECUTION COMPLETE")
    print("   Check the Dashboard to see the Final Results.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_pipeline())
