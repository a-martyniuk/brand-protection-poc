import os
import requests
import json

class MeliBPPClient:
    """
    Client for MercadoLibre's Brand Protection Program (BPP) API.
    Allows reporting Intellectual Property violations directly.
    """
    
    BASE_URL = "https://api.mercadolibre.com"
    
    def __init__(self, access_token=None, mock_mode=True):
        self.access_token = access_token or os.getenv("MELI_ACCESS_TOKEN")
        self.mock_mode = mock_mode
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def get_authorized_reasons(self):
        """
        Fetches the list of violation reasons (motives) Nutricia is authorized to use.
        """
        if self.mock_mode:
            return [
                {"id": "703", "description": "Precio significativamente inferior al sugerido"},
                {"id": "704", "description": "Información engañosa sobre cantidad/volumen"}
            ]
            
        url = f"{self.BASE_URL}/bpp/reasons"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def report_violation(self, item_id, reason_id, comment=None):
        """
        Reports an item to the BPP.
        """
        payload = {
            "item_id": item_id,
            "reason_id": reason_id,
            "description": comment or "Automatización de Brand Protection - Nutricia"
        }
        
        print(f"BPP REPORT: Reporting {item_id} for reason {reason_id}...")
        
        if self.mock_mode:
            return {
                "status": "success",
                "complaint_id": f"mock_complaint_{item_id}_{reason_id}",
                "message": "En modo MOCK: El reporte no se envió a Meli"
            }
            
        url = f"{self.BASE_URL}/bpp/items/complaints"
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code == 201:
            return {
                "status": "success",
                "complaint_id": response.json().get("id"),
                "data": response.json()
            }
        else:
            return {
                "status": "error",
                "code": response.status_code,
                "message": response.text
            }
