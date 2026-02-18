from logic.supabase_handler import SupabaseHandler

def check_counts():
    db = SupabaseHandler()
    
    # Count listings
    listings = db.supabase.table("meli_listings").select("id", count="exact").execute()
    print(f"Total listings in 'meli_listings': {listings.count}")
    
    # Count audit entries
    audits = db.supabase.table("compliance_audit").select("id", count="exact").execute()
    print(f"Total audits in 'compliance_audit': {audits.count}")
    
    # Check limit override
    audits_limit = db.supabase.table("compliance_audit").select("id").limit(2000).execute()
    print(f"Audit fetch with limit(2000) returned: {len(audits_limit.data)} rows")

if __name__ == "__main__":
    check_counts()
