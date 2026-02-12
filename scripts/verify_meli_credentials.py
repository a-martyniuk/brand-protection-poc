import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scrapers.meli_api import MeliAPIClient

load_dotenv()

def main():
    print("--- MercadoLibre Credentials Verifier (Client Credentials Flow) ---")
    
    app_id = os.getenv("MELI_APP_ID")
    client_secret = os.getenv("MELI_CLIENT_SECRET")

    print(f"App ID: {app_id}")
    print(f"Client Secret: {'*' * len(client_secret) if client_secret else 'None'}")

    if not app_id or not client_secret:
        print("\nError: MELI_APP_ID or MELI_CLIENT_SECRET not found in .env file.")
        return

    client = MeliAPIClient(app_id=app_id, client_secret=client_secret)
    
    print("\nAttempting to obtain access token...")
    token_data = client.get_access_token()
    
    if token_data and "access_token" in token_data:
        print("\n--- SUCCESS! ---")
        print("Your credentials are valid.")
        print(f"Access Token: {token_data['access_token'][:10]}...{token_data['access_token'][-10:]}")
        print(f"Expires in: {token_data.get('expires_in')} seconds")
    else:
        print("\n--- ERROR ---")
        print(f"Failed to get token. Response: {token_data}")

if __name__ == "__main__":
    main()
