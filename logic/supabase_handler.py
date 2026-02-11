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

    def upsert_products(self, products_data):
        """
        Upserts products into the 'products' table.
        Includes fields like 'thumbnail', 'seller_location', and 'is_authorized'.
        """
        try:
            response = self.supabase.table("products").upsert(
                products_data, on_conflict="meli_id"
            ).execute()
            return response.data
        except Exception as e:
            print(f"Error upserting products to Supabase: {e}")
            return None

    def get_policies(self):
        """
        Retrieves all active policies.
        """
        try:
            response = self.supabase.table("policies").select("*").execute()
            return response.data
        except Exception as e:
            print(f"Error fetching policies: {e}")
            return []

    def get_authorized_sellers(self):
        """
        Retrieves names/IDs of authorized sellers.
        """
        try:
            response = self.supabase.table("authorized_sellers").select("name").execute()
            return [s["name"] for s in response.data]
        except Exception as e:
            print(f"Error fetching authorized sellers: {e}")
            return []

    def log_violation(self, violation_data):
        """
        Inserts a new violation record.
        """
        try:
            response = self.supabase.table("violations").insert(violation_data).execute()
            return response.data
        except Exception as e:
            print(f"Error logging violation: {e}")
            return None
