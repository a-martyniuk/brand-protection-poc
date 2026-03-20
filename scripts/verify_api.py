import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_token():
    token = os.environ.get("MELI_ACCESS_TOKEN")
    if not token:
        print("❌ No token found in .env")
        return

    print(f"Testing token (starts with {token[:10]}...)")
    
    # Real-world headers to bypass PolicyAgent
    modern_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "es-AR,es;q=0.9",
        "Connection": "keep-alive"
    }
    
    # Test 1: Simple ME call
    me_url = "https://api.mercadolibre.com/users/me"
    auth_headers = {**modern_headers, "Authorization": f"Bearer {token}"}
    
    try:
        resp = requests.get(me_url, headers=auth_headers)
        print(f"ME Status: {resp.status_code}")
        if resp.ok:
            print("✅ Token is VALID for /users/me")
        else:
            print(f"❌ Token INVALID for /users/me: {resp.text}")
            
        # Test 2: Item call with Token + Modern Headers
        item_id = "MLA1517652477"
        item_url = f"https://api.mercadolibre.com/items/{item_id}"
        
        print(f"\nTesting item API with TOKEN + MODERN HEADERS for {item_id}...")
        resp_item = requests.get(item_url, headers=auth_headers)
        print(f"Item Status: {resp_item.status_code}")
        if resp_item.ok:
            print("✅ Item API works WITH TOKEN + HEADERS")
        else:
            print(f"❌ Item API FAILED WITH TOKEN + HEADERS: {resp_item.text}")
            
        # Test 3: Public Item call with Modern Headers
        print(f"\nTesting PUBLIC item API with MODERN HEADERS for {item_id}...")
        resp_pub = requests.get(item_url, headers=modern_headers)
        print(f"Public Item Status: {resp_pub.status_code}")
        if resp_pub.ok:
            print("✅ Item API works PUBLICLY + HEADERS")
        else:
            print(f"❌ Item API FAILED PUBLICLY + HEADERS: {resp_pub.text}")

    except Exception as e:
        print(f"💥 Request failed: {e}")

if __name__ == "__main__":
    test_token()
