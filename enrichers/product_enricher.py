import sys
import asyncio
import os
import json
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.getcwd())
print(f"DEBUG FILE LOCATION: {os.path.abspath(__file__)}")

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
        """
        print("\n🚀 ENRICHER VERSION: 2.1 (Intelligence + API Metadata Fix)")
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
                user_data_dir=user_data_dir,
                headless=False,
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                ignore_default_args=["--enable-automation"],
                args=["--disable-blink-features=AutomationControlled"]
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
                        if details and "metadata" in details:
                            m = details['metadata']
                            print(f"    [DEBUG] Seller: {m.get('seller_name')} | ID: {m.get('seller_id')} | Sold: {m.get('sold_quantity')}")
                        
                        # Update database and log
                        if details and (details.get('ean') or details.get('specs') or details.get('available_quantity') is not None):
                            self.update_product(product['id'], details)
                            ean = details.get('ean', 'N/A')
                            stock = details.get('available_quantity', 0)
                            
                            # Enhanced console output for Brand Protection
                            meta = details.get('metadata', {})
                            seller = meta.get('seller_name', 'Unknown')
                            if meta.get('is_official_store'):
                                seller += " [OFFICIAL]"
                            sold = meta.get('sold_quantity', 0)
                            cond = meta.get('condition', 'new')
                            
                            # Try to get price from variations or metadata if we start capturing it
                            price = meta.get('price') or "N/A"
                            
                            print(f"  ✓ {meli_id} - EAN: {ean} | Stock: {stock} | Seller: {seller} | Sold: {sold} | Cond: {cond}")
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
                
                query = self.db.supabase.table("meli_listings").select("*").not_.in_(
                    "item_status", ["noise", "noise_manual"]
                ).order(
                    "last_enriched_at", desc=False, nullsfirst=True
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
                return f"https://articulo.mercadolibre.com.ar/MLA-{mla_id}"
            return None # Skip if no ID found
        
        # Normalize any MLA URL to articulo version for better resilience
        mla_match = re.search(r'MLA-?(\d+)', url)
        if mla_match:
            mla_id = mla_match.group(1)
            return f"https://articulo.mercadolibre.com.ar/MLA-{mla_id}"
            
        return url
    
    async def scrape_product_details(self, page, url):
        """
        Scrape product detail page for EAN and specifications.
        """
        # Initialize default structure
        details = {
            "ean": None,
            "specs": {},
            "available_quantity": None,
            "metadata": {
                "seller_name": "Unknown",
                "seller_id": None,
                "sold_quantity": 0,
                "condition": "new",
                "is_official_store": False
            },
            "description": ""
        }
        
        try:
            clean_url = self.clean_url(url)
            if not clean_url:
                return None
                
            await page.goto(clean_url, wait_until="domcontentloaded", timeout=30000)
            
            # Bot/Login Wall Detection
            if any(p in page.url for p in ["account-verification", "negative_traffic", "login", "auth"]):
                print("\n" + "!"*80 + "\n🛑 BLOQUEO/LOGIN: Completa el login/captcha en Chrome y presiona ENTER...")
                await asyncio.get_event_loop().run_in_executor(None, input, "Presiona ENTER para reanudar...")
                return await self.scrape_product_details(page, url)

            # Wait for content
            try:
                winner = await page.wait_for_selector('.andes-table__row, .ui-pdp-specs__table__row, .ui-pdp-buybox__quantity__available, .ui-pdp-message', timeout=15000)
                class_handle = await winner.get_property('className')
                class_str = str(await class_handle.json_value())
                if 'ui-pdp-message' in class_str:
                    msg_text = await winner.inner_text()
                    details["specs"]["_item_status"] = "unavailable"
                    details["description"] = msg_text
                    # Still try API fallback even if unavailable in DOM
            except:
                print(f"    ⚠ Timeout/Partial load for {url}")
                # Continue to API fallback
            
            # Extract from DOM
            dom_data = await page.evaluate(r"""
                () => {
                    const state = window.__PRELOADED_STATE__?.initialState;
                    const rows = document.querySelectorAll('.andes-table__row, .ui-pdp-specs__table__row');
                    let specs = {};
                    let ean = null;
                    
                    for (const row of rows) {
                        const l = row.querySelector('.andes-table__column--label, th')?.innerText.trim();
                        const v = row.querySelector('.andes-table__column--value, td')?.innerText.trim();
                        if (l && v) {
                            specs[l] = v;
                            const lowL = l.toLowerCase();
                            if (lowL.includes('ean') || lowL.includes('código universal') || lowL.includes('gtin')) {
                                ean = v.replace(/\D/g, '');
                            }
                        }
                    }

                        const stockSelectors = ['.ui-pdp-buybox__quantity', '.ui-pdp-stock-info', '.ui-pdp-message', '.ui-pdp-promotions-pill-label'];
                        let stockText = "";
                        for (const sel of stockSelectors) {
                            const el = document.querySelector(sel);
                            if (el && el.innerText) {
                                stockText += " " + el.innerText.replace(/\n/g, ' ');
                            }
                        }
                        
                        let stock = state?.item?.data?.available_quantity || state?.components?.buybox?.quantity?.available || null;
                        
                        if (!stock && stockText) {
                            const normalized = stockText.toLowerCase();
                            // 1. Try to find "X disponibles" or "X unidades" explicitly
                            const availMatch = normalized.match(/(\d+)\s+(disponible|unidade)/);
                            if (availMatch) {
                                stock = parseInt(availMatch[1]);
                            } 
                            // 2. Handle "Última disponible" or "Único disponible"
                            else if (/[uú]ltim[ao]|[uú]nic[ao]/i.test(normalized)) {
                                stock = 1;
                            }
                            // 3. Last fallback: any number found in the text
                            else {
                                const match = normalized.match(/(\d+)/);
                                if (match) stock = parseInt(match[1]);
                            }
                        }

                        let raw_seller = state?.components?.seller?.nickname || 
                                         document.querySelector('.ui-pdp-seller__link-container')?.innerText || 
                                         document.querySelector('.ui-pdp-official-store-link')?.innerText || 
                                         document.querySelector('.ui-pdp-seller__header__title')?.innerText ||
                                         document.querySelector('.ui-pdp-action-modal--seller .ui-pdp-button--link')?.innerText ||
                                         document.body.innerText.match(/(Vendido|Ofrecido) por\s+([^\n]+)/i)?.[2] || 
                                         document.body.innerText.match(/Tienda oficial\s+([^\n]+)/i)?.[1] || 
                                         null;

                        const itemStatus = state?.item?.status || "active";
                        const unavailableMsg = document.querySelector('.ui-pdp-message')?.innerText || "";
                        
                        return {
                            ean: ean,
                            specs: specs,
                            stock: stock,
                            item_status: itemStatus,
                            status_description: unavailableMsg,
                            metadata: {
                                seller_name: raw_seller ? raw_seller.replace(/^(Vendido|Ofrecido) por\s*|Tienda oficial\s*/gi, '').replace(/\n/g, ' ').trim() : null,
                                seller_id: state?.components?.seller?.id || null,
                                sold_quantity: state?.item?.sold_quantity || state?.components?.header?.sold_quantity || 0,
                                condition: state?.item?.condition || null,
                                is_official_store: !!state?.components?.seller?.official_store_id
                            },
                            description: document.querySelector('.ui-pdp-description__content')?.innerText || ""
                        };
                    }
                """)
            
            if dom_data:
                if dom_data.get('ean'): details['ean'] = dom_data['ean']
                if dom_data.get('specs'): details['specs'].update(dom_data['specs'])
                if dom_data.get('stock') is not None: details['available_quantity'] = dom_data['stock']
                if dom_data.get('metadata'): details['metadata'].update(dom_data['metadata'])
                if dom_data.get('description'): details['description'] = dom_data['description']

            # --- API FALLBACK (Crucial for Brand Protection) ---
            meli_id = None
            mla_match = re.search(r'MLA-?(\d+)', url)
            if mla_match: meli_id = f"MLA{mla_match.group(1)}"
            
            if meli_id:
                api_url = f"https://api.mercadolibre.com/items/{meli_id}"
                try:
                    # Clean Python requests (bypasses browser fingerprinting/blocks)
                    headers = {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}
                    
                    # Try with token
                    resp = requests.get(api_url, headers=headers, timeout=10)
                    
                    # Fallback to public if failed/unauthorized
                    if not resp.ok:
                        resp = requests.get(api_url, timeout=10)
                        
                    if resp.ok:
                        api_data = resp.json()
                        details['available_quantity'] = self._parse_stock_from_data(api_data, details)
                    else:
                        print(f"    ⚠ API fallback failed for {meli_id} (Status: {resp.status_code})")
                except Exception as api_err:
                    print(f"    Warning: API fallback error: {api_err}")
            
            return details
            
        except Exception as e:
            print(f"    Error in scrape_product_details: {e}")
            return details # Return what we have

    def _parse_stock_from_data(self, data, details):
        """Helper to parse available_quantity and metadata from API response."""
        if not data:
            return 0
            
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
            
        # Extract Metadata for Brand Protection from API response
        # Note: API response structure is slightly different from DOM State
        s_id = data.get('seller_id')
        details['metadata'] = {
            'seller_id': s_id,
            'seller_name': f"ID: {s_id}" if s_id else "API_UNKNOWN", # Nickname usually requires /users call
            'is_official_store': data.get('official_store_id') is not None and data.get('official_store_id') > 0,
            'sold_quantity': data.get('sold_quantity', 0),
            'condition': data.get('condition', 'new'),
            'main_image': data.get('thumbnail') or (data.get('pictures')[0].get('url') if data.get('pictures') else None),
            'health': data.get('health')
        }
        
        return total_stock
    
    def update_product(self, product_id, details):
        """
        Update product with enriched data.
        
        Args:
            product_id: UUID of product in database
            details: dict with 'ean' and 'specs' keys
        """
        if not details:
            return
            
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
            
            if details.get('item_status'):
                update_data['item_status'] = details['item_status']
            if details.get('status_description'):
                update_data['status_description'] = details['status_description']
            
            # Sync metadata to top-level columns for frontend visibility
            meta = details.get('metadata', {})
            if meta.get('seller_name'):
                update_data['seller_name'] = meta['seller_name']
            if meta.get('seller_id'):
                update_data['seller_id'] = str(meta['seller_id'])
            if meta.get('is_official_store') is not None:
                update_data['is_official_store'] = meta['is_official_store']
            if meta.get('sold_quantity') is not None:
                update_data['sold_quantity'] = meta['sold_quantity']
            if meta.get('condition'):
                update_data['condition'] = meta['condition']
            
            update_data['last_enriched_at'] = datetime.now().isoformat()
                
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
