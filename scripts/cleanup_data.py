import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def cleanup():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    print("Cleaning up meli_listings and compliance_audit...")
    # Since compliance_audit has ON DELETE CASCADE from meli_listings, 
    # deleting all from meli_listings clears both.
    # Note: Supabase/PostgREST delete requires a filter or 'all'
    try:
        # Delete compliance_audit first just in case
        res_audit = supabase.table("compliance_audit").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"Cleared compliance_audit.")
        
        res_listings = supabase.table("meli_listings").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"Cleared meli_listings.")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup()
