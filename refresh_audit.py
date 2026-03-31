import asyncio
import requests
import sys

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

from logic.supabase_lite import SupabaseLite
from logic.identification_engine import IdentificationEngine

async def refresh_audit():
    print("Starting Audit Refresh...")
    db = SupabaseLite()
    engine = IdentificationEngine()
    
    # 1. Fetch all listings from DB (handling pagination for > 1000 rows)
    print("Fetching active listings from 'meli_listings' via SupabaseLite...")
    listings = []
    batch_size = 1000
    offset = 0
    
    while True:
        # Use requests to fetch data through REST API
        endpoint = f"{db.url}/rest/v1/meli_listings?select=*&offset={offset}&limit={batch_size}"
        try:
            res = requests.get(endpoint, headers=db.headers)
            res.raise_for_status()
            batch = res.json()
            listings.extend(batch)
            print(f"Loaded {len(listings)} listings...")
            if len(batch) < batch_size:
                break
            offset += batch_size
        except Exception as e:
            print(f"Error fetching listings: {e}")
            break
    
    print(f"Total listings loaded: {len(listings)}")
    
    # 2. Re-run identification for each
    print("Re-calculating fraud scores with precision thresholds...")
    audit_records = []
    noise_ids = []
    
    for l in listings:
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

        # Track which listings should be marked as noise
        if audit["match_level"] == 0:
            noise_ids.append(l["id"])
    
    # 3. Batch Update Listings (Status)
    active_ids = [a["listing_id"] for a in audit_records if a["match_level"] > 0]
    
    if noise_ids:
        print(f"Moving {len(noise_ids)} items to Noise status...")
        for i in range(0, len(noise_ids), 100):
            batch = noise_ids[i:i+100]
            endpoint = f"{db.url}/rest/v1/meli_listings?id=in.({','.join([str(id) for id in batch])})"
            try:
                requests.patch(endpoint, json={"item_status": "noise"}, headers=db.headers)
            except Exception as e:
                print(f"Error updating noise items: {e}")
                
    if active_ids:
        print(f"Marking {len(active_ids)} items as Active (Audited)...")
        for i in range(0, len(active_ids), 100):
            batch = active_ids[i:i+100]
            endpoint = f"{db.url}/rest/v1/meli_listings?id=in.({','.join([str(id) for id in batch])})"
            try:
                requests.patch(endpoint, json={"item_status": "active"}, headers=db.headers)
            except Exception as e:
                print(f"Error updating active items: {e}")
    
    # 4. Batch Update Audit Table
    if audit_records:
        print(f"Syncing {len(audit_records)} updated audit results to Supabase (FORCED UPSERT)...")
        for i in range(0, len(audit_records), 100):
            batch = audit_records[i:i+100]
            # Use on_conflict=listing_id to OVERWRITE existing audit entries
            endpoint = f"{db.url}/rest/v1/compliance_audit?on_conflict=listing_id"
            
            headers = db.headers.copy()
            # OMITTING resolution=merge-duplicates to force OVERWRITE (default in PostgREST is overwrite if not specified)
            
            try:
                res = requests.post(endpoint, json=batch, headers=headers)
                if res.status_code >= 400:
                    print(f"  [ERROR] Sync Batch {i//100} failed: {res.status_code} - {res.text}")
                else:
                    print(f"  [OK] Sync Batch {i//100} complete (Updated {len(batch)} records).")
            except Exception as e:
                print(f"  [CRITICAL] Sync Batch {i//100} exception: {e}")
        
        print("[OK] Audit refresh complete. New scores are now live in the Dashboard.")
    else:
        print("No listings found to audit.")

if __name__ == "__main__":
    asyncio.run(refresh_audit())
