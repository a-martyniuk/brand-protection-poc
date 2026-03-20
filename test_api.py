import requests
import sys

def test_id(meli_id):
    url = f"https://api.mercadolibre.com/items/{meli_id}"
    print(f"Testing {url}...")
    try:
        r = requests.get(url, timeout=10)
        print(f"Status: {r.status_code}")
        if r.ok:
            print(f"Stock: {r.json().get('available_quantity')}")
        else:
            print(f"Headers: {r.headers}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_id("MLA1517652477")
    test_id("MLA1129026398")
