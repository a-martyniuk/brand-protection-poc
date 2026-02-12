import os
import requests
from dotenv import load_dotenv
import sys
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scrapers.meli_api import MeliAPIClient

load_dotenv()

def test_endpoints():
    client = MeliAPIClient()
    print("Obtaining fresh token...")
    client.get_access_token()
    
    token = client.access_token
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "brand-protection-poc/1.0",
        "Accept": "application/json"
    }
    
    endpoints = [
        "/sites/MLA/search?q=Nutrilon",
        "/brand_protection/item_search?q=Nutrilon",
        "/brand_protection/seller_search?seller_id=51746963",
        "/brand_protection/itineraries",
        "/users/me",
        "/applications/" + str(client.app_id)
    ]
    
    for endpoint in endpoints:
        url = f"https://api.mercadolibre.com{endpoint}"
        print(f"\nTesting: {url}")
        try:
            response = requests.get(url, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_endpoints()
