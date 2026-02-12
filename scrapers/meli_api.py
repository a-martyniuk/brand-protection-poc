import os
import requests
import json
import time
import urllib.parse

class MeliAPIClient:
    def __init__(self, app_id=None, client_secret=None, redirect_uri=None):
        self.app_id = app_id or os.getenv("MELI_APP_ID")
        self.client_secret = client_secret or os.getenv("MELI_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("MELI_REDIRECT_URI")
        self.access_token = os.getenv("MELI_ACCESS_TOKEN")
        self.refresh_token = os.getenv("MELI_REFRESH_TOKEN")
        self.base_url = "https://api.mercadolibre.com"

    def get_access_token(self):
        """Obtains an access token using client_credentials flow (Legacy/fallback)."""
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.app_id,
            "client_secret": self.client_secret
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "brand-protection-poc/1.0",
            "Accept": "application/json"
        }
        response = requests.post(f"{self.base_url}/oauth/token", data=payload, headers=headers)
        data = response.json()
        
        if "access_token" in data:
            self.access_token = data["access_token"]
            return data
        return None

    def exchange_code_for_token(self, code):
        """Exchanges the authorization code for an access token."""
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.app_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "brand-protection-poc/1.0",
            "Accept": "application/json"
        }
        response = requests.post(f"{self.base_url}/oauth/token", data=payload, headers=headers)
        return response.json()

    def refresh_access_token(self):
        """Refreshes the access token using the refresh token if available, else fallback."""
        if not self.refresh_token:
            return self.get_access_token()
            
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.app_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "brand-protection-poc/1.0",
            "Accept": "application/json"
        }
        response = requests.post(f"{self.base_url}/oauth/token", data=payload, headers=headers)
        data = response.json()
        
        if "access_token" in data:
            self.access_token = data["access_token"]
            self.refresh_token = data.get("refresh_token", self.refresh_token)
            print("Token refreshed successfully.")
        else:
            print(f"Error refreshing token: {data}")
            
        return data

    def _get(self, endpoint, params=None):
        """Generic GET request with token refresh handling."""
        headers = {
            "Authorization": f"Bearer {self.access_token}" if self.access_token else "",
            "User-Agent": "brand-protection-poc/1.0",
            "Accept": "application/json",
        }
        url = f"{self.base_url}{endpoint}"
        
        response = requests.get(url, headers=headers, params=params)
        print(f"API Request: {url} -> {response.status_code}")
        
        if response.status_code == 401:
            print("Token expired or invalid. Attempting refresh...")
            refresh_data = self.refresh_access_token()
            if refresh_data and "access_token" in refresh_data:
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = requests.get(url, headers=headers, params=params)
        
        return response

    def search_products(self, query, site_id="MLA", offset=0, limit=50):
        """Searches for products in a specific site (default MLA)."""
        params = {
            "q": query,
            "offset": offset,
            "limit": limit
        }
        response = self._get(f"/sites/{site_id}/search", params=params)
        
        if response.status_code == 200:
            return response.json()
        
        print(f"Search failed: {response.status_code} - {response.text}")
        return None

    def get_item_details(self, item_id):
        """Get details for a specific item."""
        response = self._get(f"/items/{item_id}")
        if response.status_code == 200:
            return response.json()
        return None
