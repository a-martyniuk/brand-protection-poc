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
        Inserts audit results into the 'compliance_audit' table.
        """
        try:
            response = self.supabase.table("compliance_audit").insert(audit_data).execute()
            return response.data
        except Exception as e:
            print(f"Error logging compliance audit: {e}")
            return None

    def get_master_products(self, brand=None):
        """
        Retrieves all master products to use as the source of truth.
        """
        try:
            query = self.supabase.table("master_products").select("*")
            if brand:
                query = query.eq("brand", brand)
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Error fetching master products: {e}")
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
