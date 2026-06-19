import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseHandler:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")
        self.supabase: Client = create_client(url, key)

    def clear_all_data(self):
        """
        Deletes all data from 'compliance_audit' and 'meli_listings' tables.
        Ensures a completely fresh start for the monthly pipeline.
        """
        try:
            print("🧹 [PHASE 0] Starting deep database reset...")
            
            # Delete compliance_audit first (due to foreign key dependencies)
            print("  - Purging 'compliance_audit'...")
            self.supabase.table("compliance_audit").delete().neq("match_level", -1).execute()
            
            # Delete meli_listings
            print("  - Purging 'meli_listings'...")
            self.supabase.table("meli_listings").delete().neq("price", -1).execute()
            
            print("✅ Database reset successful (Absolute Zero).")
            return True
        except Exception as e:
            print(f"❌ Error during database reset: {e}")
            return False

    def upsert_master_products(self, products_data):
        """
        Upserts products into the 'master_products' table.
        Used for populating the Golden Source.
        """
        try:
            response = self.supabase.table("master_products").upsert(
                products_data, on_conflict="ean"
            ).execute()
            return response.data
        except Exception as e:
            print(f"Error upserting master products: {e}")
            return None

    def upsert_meli_listings(self, listings_data):
        """
        Upserts scraped data into the 'meli_listings' table.
        """
        try:
            response = self.supabase.table("meli_listings").upsert(
                listings_data, on_conflict="meli_id"
            ).execute()
            return response.data
        except Exception as e:
            print(f"Error upserting Meli listings: {e}")
            return None

    def log_compliance_audit(self, audit_data):
        """
        Upserts audit results into the 'compliance_audit' table.
        """
        try:
            response = self.supabase.table("compliance_audit").upsert(
                audit_data, on_conflict="listing_id"
            ).execute()
            return response.data
        except Exception as e:
            print(f"Error logging compliance audit: {e}")
            return None

    def get_master_products(self, brand=None):
        """
        Retrieves all master products using pagination to bypass the 1000 limit.
        """
        try:
            all_data = []
            page_size = 1000
            start = 0
            
            while True:
                query = self.supabase.table("master_products").select("*").range(start, start + page_size - 1)
                if brand:
                    query = query.eq("brand", brand)
                
                response = query.execute()
                data = response.data
                all_data.extend(data)
                
                if len(data) < page_size:
                    break
                start += page_size
                
            return all_data
        except Exception as e:
            print(f"Error fetching master products: {e}")
            return []

    def get_meli_listings(self):
        """
        Retrieves all listings using pagination to bypass the 1000 limit.
        """
        try:
            all_data = []
            page_size = 1000
            start = 0
            
            while True:
                response = self.supabase.table("meli_listings").select("*").range(start, start + page_size - 1).execute()
                data = response.data
                all_data.extend(data)
                
                if len(data) < page_size:
                    break
                start += page_size
                
            return all_data
        except Exception as e:
            print(f"Error fetching Meli listings: {e}")
            return []

    # Keeping legacy methods for transition if needed, but updating to use new tables internally
    def get_official_products(self):
        return self.get_master_products()

    def upsert_products(self, products_data):
        # Redirecting to listings for compatibility during refactor
        return self.upsert_meli_listings(products_data)

    def log_violation(self, violation_data):
        # Violations are now part of compliance_audit, but keeping this simple for now
        print("Legacy log_violation called. Please use log_compliance_audit.")
        return None
