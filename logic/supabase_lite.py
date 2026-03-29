
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
            "Content-Type": "application/json"
        }

    def upsert_meli_listings(self, listings_data):
        """
        Upserts scraped data into the 'meli_listings' table using requests.
        If a batch fails with a conflict error, it retries item by item 
        to ensure progress and isolate problematic records.
        """
        if not listings_data:
            return True
            
        endpoint = f"{self.url}/rest/v1/meli_listings?on_conflict=meli_id"
        headers = self.headers.copy()
        headers["Prefer"] = "resolution=merge-duplicates"
        
        try:
            response = requests.post(endpoint, json=listings_data, headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            # Check for conflict error (21000 or similar 500/400)
            status_code = getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
            
            if status_code >= 400:
                print(f"Batch upsert failed ({status_code}). Retrying item by item...")
                success_count = 0
                for i, item in enumerate(listings_data):
                    try:
                        # For single items, we don't need on_conflict in the param (usually)
                        # but in PostgREST we do it for parity
                        res = requests.post(endpoint, json=item, headers=headers)
                        res.raise_for_status()
                        success_count += 1
                    except Exception as ie:
                        # Silent skip for individual bad items
                        pass
                print(f"  - Rescued {success_count}/{len(listings_data)} items from the batch.")
                return success_count > 0
            
            print(f"Unexpected error in upsert: {e}")
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
