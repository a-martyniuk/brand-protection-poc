
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SupabaseLite:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set.")
        
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

    def upsert_meli_listings(self, listings_data):
        """
        Upserts scraped data into the 'meli_listings' table using requests.
        Uses on_conflict query param for proper PostgREST upsert.
        """
        # We target meli_id for conflict resolution
        endpoint = f"{self.url}/rest/v1/meli_listings?on_conflict=meli_id"
        headers = self.headers.copy()
        headers["Prefer"] = "resolution=merge-duplicates"
        
        try:
            response = requests.post(endpoint, json=listings_data, headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error upserting Meli listings (Lite): {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Detail: {e.response.text}")
            return False

    def get_master_products(self):
        """
        Retrieves all master products (simplified).
        """
        endpoint = f"{self.url}/rest/v1/master_products?select=*"
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching master products (Lite): {e}")
            return []
