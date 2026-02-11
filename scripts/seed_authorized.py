import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def seed_authorized_sellers():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Authorized sellers for the PoC
    sellers = [
        {"name": "NUTRICIA OFICIAL STORE"},
        {"name": "BAGO OFICIAL STORE"},
        {"name": "Farmacity"},
        {"name": "Farmacia Central"}
    ]
    
    try:
        # Check if table exists by trying to select (this might fail if table not created yet)
        # In a real scenario, we'd run SQL migrations first.
        # Here we just try to insert.
        print("Seeding authorized sellers...")
        supabase.table("authorized_sellers").upsert(sellers, on_conflict="name").execute()
        print("Done!")
    except Exception as e:
        print(f"Error seeding: {e}")
        print("Note: If the table doesn't exist, you may need to run the SQL migration in Supabase.")

if __name__ == "__main__":
    seed_authorized_sellers()
