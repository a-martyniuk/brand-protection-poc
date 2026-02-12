import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scrapers.meli_api import MeliAPIClient

load_dotenv()

def exchange(code):
    client = MeliAPIClient()
    print(f"Exchanging code: {code}")
    print(f"Redirect URI: {client.redirect_uri}")
    
    data = client.exchange_code_for_token(code)
    
    if "access_token" in data:
        print("\n--- Success! ---")
        print(f"Access Token: {data['access_token']}")
        refresh_token = data.get("refresh_token")
        if refresh_token:
            print(f"Refresh Token: {refresh_token}")
        else:
            print("Refresh Token: Not provided (scope 'offline_access' might be missing)")
            
        # Update .env file
        env_path = ".env"
        if not os.path.exists(env_path):
             print(f"Error: {env_path} not found.")
             return
             
        with open(env_path, "r") as f:
            lines = f.readlines()
            
        new_lines = []
        updated_keys = {"MELI_ACCESS_TOKEN": data['access_token']}
        if refresh_token:
            updated_keys["MELI_REFRESH_TOKEN"] = refresh_token
        
        seen_keys = set()
        for line in lines:
            updated = False
            for key, val in updated_keys.items():
                if line.startswith(f"{key}="):
                    new_lines.append(f"{key}={val}\n")
                    seen_keys.add(key)
                    updated = True
                    break
            if not updated:
                new_lines.append(line)
        
        # Add keys if they weren't in the file
        for key, val in updated_keys.items():
            if key not in seen_keys:
                new_lines.append(f"{key}={val}\n")
                
        with open(env_path, "w") as f:
            f.writelines(new_lines)
            
        print("\n.env file updated successfully.")
    else:
        print("\n--- Error ---")
        print(data)

if __name__ == "__main__":
    code = "TG-698d342141f16b0001f7868f-51746963"
    exchange(code)
