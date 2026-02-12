import os
import json
import requests
from datetime import datetime
from logic.supabase_handler import SupabaseHandler
import time

class MeliAPIEnricher:
    """
    Enricher that uses MercadoLibre's official API to get product details.
    Much more reliable than scraping and doesn't get blocked.
    """
    
    def __init__(self, batch_size=50, delay_between_requests=0.5):
        self.db = SupabaseHandler()
        self.batch_size = batch_size
        self.delay = delay_between_requests
        self.status_file = "enricher_status.json"
        self.access_token = os.getenv("MELI_ACCESS_TOKEN")
        self.progress = {
            "running": False,
            "started_at": None,
            "last_update": None,
            "total_products": 0,
            "processed": 0,
            "enriched": 0,
            "failed": 0,
            "current_product": None,
            "history": []
        }
        
    def update_status(self, **kwargs):
        """Update status file with current progress."""
        self.progress.update(kwargs)
        self.progress["last_update"] = datetime.now().isoformat()
        
        with open(self.status_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def log_product(self, meli_id, status, ean=None, error=None):
        """Log individual product processing."""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "meli_id": meli_id,
            "status": status,
            "ean": ean,
            "error": error
        }
        self.progress["history"].append(log_entry)
        
        # Keep only last 100 entries
        if len(self.progress["history"]) > 100:
            self.progress["history"] = self.progress["history"][-100:]
    
    def enrich_products(self, limit=None):
        """
        Enrich products using MercadoLibre API.
        
        Args:
            limit: Maximum number of products to enrich (None = all)
        """
        # Get products needing enrichment
        products = self.get_products_to_enrich(limit)
        
        # Initialize status
        self.update_status(
            running=True,
            started_at=datetime.now().isoformat(),
            total_products=len(products),
            processed=0,
            enriched=0,
            failed=0
        )
        
        print(f"🔍 Found {len(products)} products to enrich")
        print(f"📊 Status tracking: {self.status_file}")
        
        if not products:
            print("✓ No products need enrichment")
            self.update_status(running=False)
            return
        
        for i, product in enumerate(products):
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                meli_id = product['meli_id']
                
                # Update current status
                self.update_status(
                    current_product={
                        "meli_id": meli_id,
                        "title": product['title'][:50],
                        "timestamp": timestamp
                    },
                    processed=i
                )
                
                print(f"\n[{timestamp}] [{i+1}/{len(products)}] {meli_id}")
                print(f"  📄 {product['title'][:60]}...")
                
                # Get details from API
                details = self.get_item_details(meli_id)
                
                # Update database and log
                if details and details.get('ean'):
                    self.update_product(product['id'], details)
                    ean = details.get('ean')
                    brand = details.get('brand', 'N/A')
                    print(f"  ✓ Enriched - EAN: {ean}, Brand: {brand}")
                    
                    self.log_product(meli_id, "enriched", ean=ean)
                    self.progress["enriched"] += 1
                else:
                    print(f"  ⚠ No EAN found in API response")
                    self.log_product(meli_id, "no_data")
                
                # Rate limiting
                time.sleep(self.delay)
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
                self.log_product(meli_id, "failed", error=str(e))
                self.progress["failed"] += 1
                continue
            finally:
                self.progress["processed"] = i + 1
                self.update_status()
        
        # Final status update
        self.update_status(
            running=False,
            current_product=None
        )
        
        print("\n" + "=" * 80)
        print(f"✓ Enrichment complete:")
        print(f"  - Total processed: {self.progress['processed']}/{len(products)}")
        print(f"  - Enriched: {self.progress['enriched']}")
        print(f"  - Failed: {self.progress['failed']}")
        print(f"  - No data: {self.progress['processed'] - self.progress['enriched'] - self.progress['failed']}")
        print("=" * 80)
    
    def get_products_to_enrich(self, limit=None):
        """Get products that need enrichment."""
        try:
            query = self.db.supabase.table("meli_listings").select("*").or_(
                "ean_published.is.null,brand_detected.is.null"
            )
            
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Error fetching products: {e}")
            return []
    
    def get_item_details(self, meli_id):
        """
        Get item details from MercadoLibre API.
        Handles both catalog products and regular items.
        
        Args:
            meli_id: MercadoLibre item ID (e.g., MLA123456)
            
        Returns:
            dict with 'ean', 'brand', and other attributes
        """
        try:
            # Try catalog endpoint first (for official products)
            catalog_url = f"https://api.mercadolibre.com/products/{meli_id}"
            
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.get(catalog_url, headers=headers, timeout=10)
            
            # If catalog fails with 404, try items endpoint
            if response.status_code == 404:
                item_url = f"https://api.mercadolibre.com/items/{meli_id}"
                response = requests.get(item_url, headers=headers, timeout=10)
            
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant info
            details = {
                "ean": None,
                "brand": None,
                "attributes": {}
            }
            
            # Parse attributes (works for both catalog and items)
            attributes = data.get("attributes", [])
            
            # For catalog products, attributes might be in a different structure
            if not attributes and "main_features" in data:
                # Convert main_features to attributes format
                attributes = [
                    {"id": f["key"], "name": f["key"], "value_name": f["value"]}
                    for f in data.get("main_features", [])
                ]
            
            for attr in attributes:
                attr_id = str(attr.get("id", "")).lower()
                attr_name = str(attr.get("name", "")).lower()
                value = attr.get("value_name") or attr.get("value_struct", {}).get("number")
                
                # EAN / GTIN
                if attr_id in ["gtin", "ean"] or "ean" in attr_name or "gtin" in attr_name:
                    details["ean"] = str(value) if value else None
                
                # Brand
                if attr_id == "brand" or "marca" in attr_name or attr_id == "marca":
                    details["brand"] = value
                
                # Store all attributes
                if value:
                    details["attributes"][attr.get("name", attr_id)] = value
            
            # Also check top-level fields for catalog products
            if not details["brand"] and "brand" in data:
                details["brand"] = data["brand"]
            
            if not details["ean"] and "gtin" in data:
                details["ean"] = data["gtin"]
            
            return details
            
        except requests.exceptions.RequestException as e:
            print(f"    API Error: {e}")
            return None
    
    def update_product(self, product_id, details):
        """Update product with enriched data."""
        try:
            update_data = {}
            
            if details.get('ean'):
                update_data['ean_published'] = details['ean']
            
            if details.get('brand'):
                update_data['brand_detected'] = details['brand']
            
            # Update attributes
            if details.get('attributes'):
                current = self.db.supabase.table("meli_listings").select("attributes").eq("id", product_id).execute()
                current_attrs = current.data[0]['attributes'] if current.data else {}
                
                # Merge attributes
                current_attrs.update(details['attributes'])
                update_data['attributes'] = current_attrs
            
            # Mark as enriched
            update_data['enriched_at'] = 'now()'
            
            if update_data:
                self.db.supabase.table("meli_listings").update(update_data).eq("id", product_id).execute()
                
        except Exception as e:
            print(f"    Error updating product: {e}")

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    
    print("=" * 60)
    print("MELI API ENRICHER - Using Official API")
    print("=" * 60)
    print(f"Batch size: {batch_size}")
    print(f"Delay between requests: {delay}s")
    if limit:
        print(f"Limit: {limit} products")
    print("=" * 60)
    
    enricher = MeliAPIEnricher(batch_size=batch_size, delay_between_requests=delay)
    enricher.enrich_products(limit=limit)
