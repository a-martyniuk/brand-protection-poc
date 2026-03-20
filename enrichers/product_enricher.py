import sys
import asyncio
import os
import json
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.getcwd())

from playwright.async_api import async_playwright
from logic.supabase_handler import SupabaseHandler
import time
import random
import re
import requests

class ProductEnricher:
    """
    Background enricher that scrapes product detail pages to extract EAN and specifications.
    Runs in batches with rate limiting to avoid blocking.
    """
    
    def __init__(self, batch_size=1, delay_between_requests=5):
        self.db = SupabaseHandler()
        self.batch_size = batch_size
        self.delay = delay_between_requests
        self.status_file = "enricher_status.json"
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
        self.access_token = os.environ.get("MELI_ACCESS_TOKEN")
        
    def update_status(self, **kwargs):
        """Update status file with current progress."""
        self.progress.update(kwargs)
        self.progress["last_update"] = datetime.now().isoformat()
        
        with open(self.status_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def log_product(self, meli_id, url, status, ean=None, stock=None, error=None):
        """Log individual product processing."""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "meli_id": meli_id,
            "url": url,
            "status": status,
            "ean": ean,
            "stock": stock,
            "error": error
        }
        self.progress["history"].append(log_entry)
        
        # Keep only last 100 entries in memory
        if len(self.progress["history"]) > 100:
            self.progress["history"] = self.progress["history"][-100:]
        
    async def enrich_products(self, limit=None):
        """
        Enrich products missing EAN or detailed specs.
        
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
        
        user_data_dir = os.path.join(os.getcwd(), "user_data", "manual_session_hotspot")
        os.makedirs(user_data_dir, exist_ok=True)
        
        async with async_playwright() as p:
            print(f"Launching persistent context in {user_data_dir} (HEADED for login)...")
            context = await p.chromium.launch_persistent_context(
                user_data_dir,
                channel="chrome",
                headless=False, # Show it so user can login if needed
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            semaphore = asyncio.Semaphore(1) # STRICT SERIAL PROCESSING for stability
            
            async def enriched_task(i, product, page_for_task):
                async with semaphore:
                    try:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        meli_id = product['meli_id']
                        url = product['url']
                        
                        self.update_status(
                            current_product={
                                "meli_id": meli_id,
                                "title": product['title'][:50],
                                "url": url,
                                "timestamp": timestamp
                            }
                        )
                        
                        print(f"[{timestamp}] [{i+1}/{len(products)}] Processing {meli_id}...")
                        
                        # Scrape detail page
                        details = await self.scrape_product_details(page_for_task, url)
                        
                        # Update database and log
                        if details and (details.get('ean') or details.get('specs') or details.get('available_quantity') is not None):
                            self.update_product(product['id'], details)
                            ean = details.get('ean', 'N/A')
                            stock = details.get('available_quantity', 0)
                            print(f"  ✓ {meli_id} - EAN: {ean} | Stock: {stock}")
                            self.log_product(meli_id, url, "enriched", ean=ean, stock=stock)
                            self.progress["enriched"] += 1
                        else:
                            print(f"  ⚠ {meli_id} - No additional data")
                            self.log_product(meli_id, url, "no_data")
                        
                        self.progress["processed"] += 1
                        self.update_status()
                        
                    except Exception as e:
                        print(f"  ✗ {meli_id} Error: {e}")
                        self.log_product(meli_id, url, "failed", error=str(e))
                        self.progress["failed"] += 1

            # Create a single page for serial processing
            page = await context.new_page()
            
            for i, product in enumerate(products):
                await enriched_task(i, product, page)
                if i < len(products) - 1:
                    # Randomized wait between 7-14 seconds
                    wait_time = random.uniform(7, 14)
                    print(f"  Waiting {wait_time:.1f}s to avoid detection...")
                    await asyncio.sleep(wait_time)
            
            await page.close()
            await context.close()
        
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
        """
        Get products that need enrichment (missing EAN or brand).
        Uses pagination to bypass the 1000 limit.
        """
        try:
            all_products = []
            page_size = 1000
            start = 0
            
            while True:
                # Calculate current range
                current_end = start + page_size - 1
                
                # If we have a limit, ensure we don't fetch more than needed
                if limit and current_end >= limit:
                    current_end = limit - 1
                
                query = self.db.supabase.table("meli_listings").select("*, compliance_audit!inner(*)").or_(
                    "ean_published.is.null,brand_detected.is.null"
                ).range(start, current_end)
                
                response = query.execute()
                data = response.data
                all_products.extend(data)
                
                # Break if we've reached the end of the data or our requested limit
                if len(data) < page_size or (limit and len(all_products) >= limit):
                    break
                    
                start += page_size
                
            return all_products[:limit] if limit else all_products
        except Exception as e:
            print(f"Error fetching products: {e}")
            return []
    
    def clean_url(self, url):
        """
        Clean tracking URLs and extract actual product URL.
        """
        if not url or url == 'N/A':
            return None
            
        import re
        
        # Skip or fix tracking URLs (click1.mercadolibre.com)
        if 'click1.mercadolibre.com' in url or 'mclics' in url:
            # Try to extract MLA ID from anywhere in the string
            mla_match = re.search(r'MLA-?(\d+)', url)
            if mla_match:
                mla_id = mla_match.group(1)
                return f"https://www.mercadolibre.com.ar/p/MLA{mla_id}"
            return None # Skip if no ID found
        
        # Remove tracking parameters from normal URLs
        if '?' in url:
            base_url = url.split('?')[0]
            return base_url
            
        return url
    
    async def scrape_product_details(self, page, url):
        """
        Scrape product detail page for EAN and specifications.
        
        Args:
            page: Playwright page object
            url: Product URL
            
        Returns:
            dict with 'ean', 'specs', 'available_quantity', etc.
        """
        try:
            # Clean URL first
            clean_url = self.clean_url(url)
            if not clean_url:
                return None
                
            await page.goto(clean_url, wait_until="domcontentloaded", timeout=30000)
            
            # --- Detection of Login/Bot Walls ---
            if "account-verification" in page.url or "negative_traffic" in page.url:
                print("\n" + "!"*80)
                print("🛑 BLOQUEO DETECTADO: MercadoLibre pide verificación humana.")
                print(f"URL Actual: {page.url}")
                print("👉 Por favor, ve a la ventana de Chrome y completa el login o captcha.")
                print("👉 Una vez que veas el producto cargado, presiona ENTER aquí para seguir...")
                print("!"*80 + "\n")
                # Use run_in_executor to not block the event loop
                await asyncio.get_event_loop().run_in_executor(None, input, "Presiona ENTER para reanudar...")
                # Try to go to the URL again now that we are "clean"
                return await self.scrape_product_details(page, url)

            # Wait for specs table or error indicators
            try:
                # ui-pdp-message is used for 'Item not available' or 'Restricted'
                winner = await page.wait_for_selector('.andes-table__row, .ui-pdp-specs__table__row, .ui-pdp-message', timeout=30000)
                
                # Check if it was an error message
                class_handle = await winner.get_property('className')
                class_str = await class_handle.json_value()
                if 'ui-pdp-message' in class_str:
                    msg_text = await winner.inner_text()
                    print(f"    ⚠ Item Unavailable: {msg_text.strip()[:50]}")
                    return {"ean": None, "specs": {"_item_status": "unavailable"}, "description": msg_text}
            except Exception as wait_err:
                # If nothing found, it might be a login challenge or blank page
                print(f"    ⚠ Timeout/Unknown state for {url}")
                return None
            
            # Extract EAN, specs and description from DOM and State
            details = await page.evaluate(r"""
                () => {
                    const rows = document.querySelectorAll('.andes-table__row, .ui-pdp-specs__table__row');
                    let ean = null;
                    let specs = {};
                    
                    // 1. Extract All Specs
                    for (const row of rows) {
                        const labelEl = row.querySelector('.andes-table__column--label, th');
                        const valueEl = row.querySelector('.andes-table__column--value, td');
                        
                        if (labelEl && valueEl) {
                            const label = labelEl.innerText.trim();
                            const value = valueEl.innerText.trim();
                            const labelLower = label.toLowerCase();
                            
                            specs[label] = value;
                            
                            if (labelLower.includes('ean') || labelLower.includes('gtin') || labelLower.includes('código universal')) {
                                ean = value.replace(/\D/g, '');
                            }
                            if (labelLower.includes('unidades por pack') || labelLower.includes('unidades por envase') || labelLower.includes('cantidad de unidades')) {
                                specs.units_per_pack = value;
                            }
                            if (labelLower.includes('tipo de leche') || labelLower.includes('tipo de suplemento') || labelLower.includes('sustancia') || labelLower.includes('tipo de producto')) {
                                specs.substance = value;
                            }
                            if (labelLower.includes('peso neto') || labelLower.includes('contenido neto') || labelLower.includes('volumen')) {
                                specs.net_content = value;
                            }
                            if (labelLower.includes('etapa') || labelLower.includes('edad mínima') || labelLower.includes('edad recomendada')) {
                                specs.stage = value;
                            }
                        }
                    }

                    // 2. Available Quantity (Stock) & Metadata
                    let stock = null;
                    let metadata = {};
                    try {
                        const state = window.__PRELOADED_STATE__?.initialState;
                        const item = state?.item;
                        const components = state?.components;

                        // Stock Extraction (Multi-priority)
                        if (item?.data) stock = item.data.available_quantity;
                        if (stock === null && components?.buybox?.quantity) stock = components.buybox.quantity.available;
                        if (stock === null) {
                            const stockEl = document.querySelector('.ui-pdp-buybox__quantity__available');
                            if (stockEl) {
                                const match = stockEl.innerText.match(/(\d+)/);
                                if (match) stock = parseInt(match[1]);
                            }
                        }

                        // Advanced Metadata for Brand Protection
                        metadata = {
                            seller_name: components?.seller?.nickname || null,
                            seller_id: components?.seller?.id || null,
                            seller_reputation: components?.reputation?.level_id || components?.seller?.reputation?.level_id || null,
                            is_official_store: !!components?.seller?.official_store_id,
                            sold_quantity: item?.sold_quantity || 0,
                            condition: item?.condition || null,
                            main_image: item?.pictures?.[0]?.url || null,
                            health: item?.health || null
                        };
                    } catch (e) {}

                    return {
                        ean: ean,
                        specs: specs,
                        available_quantity: stock,
                        metadata: metadata,
                        description: document.querySelector('.ui-pdp-description__content')?.innerText || ""
                    };
                }
            """)
            
            # --- API FALLBACK FOR STOCK ---
            meli_id = None
            mla_match = re.search(r'MLA-?(\d+)', url)
            if mla_match:
                meli_id = f"MLA{mla_match.group(1)}"
            
            if meli_id:
                try:
                    # Use page.request to stay within the same session context
                    api_url = f"https://api.mercadolibre.com/items/{meli_id}"
                    
                    async def fetch_stock(use_token=True):
                        headers = {}
                        if use_token and self.access_token:
                            headers["Authorization"] = f"Bearer {self.access_token}"
                        return await page.request.get(api_url, headers=headers)

                    response = await fetch_stock(use_token=True)
                    
                    if response.status == 401 and self.access_token:
                        print(f"    Notice: Token expired/invalid for {meli_id}, trying public API...")
                        response = await fetch_stock(use_token=False)

                    if response.ok:
                        data = await response.json()
                        details['available_quantity'] = self._parse_stock_from_data(data, details)
                    
                    if (details.get('available_quantity') is None or details.get('available_quantity') == 0):
                        # Final Attempt: Clean Python requests (bypasses browser fingerprinting)
                        print(f"    Notice: Browser API failed ({response.status}), trying clean Python request...")
                        try:
                            resp = requests.get(api_url, timeout=10)
                            if resp.ok:
                                details['available_quantity'] = self._parse_stock_from_data(resp.json(), details)
                        except: pass
                        
                except Exception as api_err:
                    print(f"    Warning: API stock fetch failed for {meli_id}: {api_err}")
            
            return details
            
        except Exception as e:
            print(f"    Error scraping {url}: {e}")
            return None

    def _parse_stock_from_data(self, data, details):
        """Helper to parse available_quantity and variations from API response."""
        total_stock = data.get("available_quantity", 0)
        variations = data.get("variations", [])
        
        if variations:
            # Sum up stock from all variations
            total_stock = sum([v.get("available_quantity", 0) for v in variations])
            details['variations_data'] = [
                {
                    "id": v.get("id"),
                    "stock": v.get("available_quantity"),
                    "price": v.get("price"),
                    "attributes": {a.get("name"): a.get("value_name") for a in v.get("attribute_combinations", [])}
                } for v in variations
            ]
        return total_stock
    
    def update_product(self, product_id, details):
        """
        Update product with enriched data.
        
        Args:
            product_id: UUID of product in database
            details: dict with 'ean' and 'specs' keys
        """
        try:
            update_data = {}
            
            # If no brand is detected, we mark it as 'Unknown' so it's not re-scraped next time
            brand_to_store = details.get('specs', {}).get('brand')
            current_brand_query = self.db.supabase.table("meli_listings").select("brand_detected").eq("id", product_id).execute()
            current_brand = current_brand_query.data[0]['brand_detected'] if current_brand_query.data else None
            
            if not current_brand:
                update_data['brand_detected'] = brand_to_store if brand_to_store else 'Unknown'
            elif brand_to_store:
                update_data['brand_detected'] = brand_to_store
                
            if details.get('ean'):
                update_data['ean_published'] = details['ean']
            
            if details.get('available_quantity') is not None:
                update_data['available_quantity'] = details['available_quantity']
                
            # Update attributes with all specs, description, variations, and advanced metadata
            if details.get('specs') or details.get('description') or details.get('variations_data') or details.get('metadata'):
                # Fetch current attributes
                current = self.db.supabase.table("meli_listings").select("attributes").eq("id", product_id).execute()
                current_attrs = current.data[0]['attributes'] if current.data else {}
                
                # Merge ALL specs from details
                if details.get('specs'):
                    for key, value in details['specs'].items():
                        current_attrs[key] = value
                
                # Add description
                if details.get('description'):
                    current_attrs['description_long'] = details['description']
                
                # Add variations data
                if details.get('variations_data'):
                    current_attrs['variations_breakdown'] = details['variations_data']

                # Add advanced metadata (Seller, Reputation, etc.)
                if details.get('metadata'):
                    for key, value in details['metadata'].items():
                        current_attrs[f"meta_{key}"] = value
                
                # Marker for last enrichment
                current_attrs['_last_enrichment_attempt'] = datetime.now().isoformat()
                update_data['attributes'] = current_attrs
            
            if update_data:
                self.db.supabase.table("meli_listings").update(update_data).eq("id", product_id).execute()
                
        except Exception as e:
            print(f"    Error updating product: {e}")

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    delay = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    print("=" * 60)
    print("PRODUCT ENRICHER - Background Deep Scraping")
    print("=" * 60)
    print("Batch size:", batch_size)
    print("Delay: Randomized (7-14s) for speed ⚡")
    print("Limit:", limit, "products")
    print("=" * 60)
    
    enricher = ProductEnricher(batch_size=batch_size, delay_between_requests=delay)
    asyncio.run(enricher.enrich_products(limit=limit))
