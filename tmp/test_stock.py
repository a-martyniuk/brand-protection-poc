import os
import asyncio
import json
import requests
from dotenv import load_dotenv

async def test_enrich():
    load_dotenv()
    token = os.environ.get("MELI_ACCESS_TOKEN")
    print(f"Testing with Token: {token[:15]}...")
    
    # Sample IDs from the user's Nutrilon scan
    ids = ["MLA10395682", "MLA9209971", "MLA9209972"]
    url = f"https://api.mercadolibre.com/items?ids={','.join(ids)}"
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    print(f"Requesting: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            for item in data:
                code = item.get("code")
                body = item.get("body", {})
                mid = body.get("id", "Unknown")
                stock = body.get("available_quantity", "N/A")
                vars_count = len(body.get("variations", []))
                print(f"ID: {mid} | Code: {code} | Stock: {stock} | Variations: {vars_count}")
                if vars_count > 0:
                    v_sum = sum(v.get("available_quantity", 0) for v in body.get("variations", []))
                    print(f"  -> Variations Sum: {v_sum}")
        else:
            print(f"Error Body: {r.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_enrich())
