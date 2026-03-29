
import sys
import os
import requests

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from logic.supabase_lite import SupabaseLite

def cleanup_db():
    print("Starting Database Cleanup...")
    db = SupabaseLite()
    
    # 1. Clear compliance_audit (FK dependency)
    print("  - Clearing compliance_audit...")
    endpoint_audit = f"{db.url}/rest/v1/compliance_audit"
    res_audit = requests.delete(endpoint_audit, params={"id": "not.is.null"}, headers=db.headers)
    if res_audit.status_code in [200, 204]:
        print("    [OK] compliance_audit cleared.")
    else:
        print(f"    [FAIL] Error clearing audit: {res_audit.text}")

    # 2. Clear meli_listings
    print("  - Clearing meli_listings...")
    endpoint_listings = f"{db.url}/rest/v1/meli_listings"
    res_listings = requests.delete(endpoint_listings, params={"id": "not.is.null"}, headers=db.headers)
    if res_listings.status_code in [200, 204]:
        print("    [OK] meli_listings cleared.")
    else:
        print(f"    [FAIL] Error clearing listings: {res_listings.text}")

    print("Database cleanup process finished.")

if __name__ == "__main__":
    cleanup_db()
