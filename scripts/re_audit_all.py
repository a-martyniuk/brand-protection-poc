import sys
import os
import asyncio
from datetime import datetime

# Add the project root to the path so we can import logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.supabase_handler import SupabaseHandler
from logic.identification_engine import IdentificationEngine

async def re_audit():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Full Database Re-Audit...")
    db = SupabaseHandler()
    engine = IdentificationEngine()
    
    # Fetch all listings from DB
    response = db.supabase.table("meli_listings").select("*").execute()
    listings = response.data
    print(f"Processing {len(listings)} listings...")
    
    audit_results = []
    for listing in listings:
        # Re-identify and audit with NEW logic
        audit_report = engine.identify_product(listing)
        audit_report["listing_id"] = listing["id"]
        audit_results.append(audit_report)
    
    if audit_results:
        print(f"Uploading {len(audit_results)} updated audit reports to Supabase...")
        # Since we use an custom upsert/log method in SupabaseHandler, let's use it
        # Actually, let's just clear compliance_audit and insert fresh to be sure
        db.supabase.table("compliance_audit").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        
        # Batch upload
        batch_size = 100
        for i in range(0, len(audit_results), batch_size):
            batch = audit_results[i:i+batch_size]
            db.log_compliance_audit(batch)
            print(f"Uploaded batch {i//batch_size + 1}")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Re-Audit complete.")

if __name__ == "__main__":
    asyncio.run(re_audit())
