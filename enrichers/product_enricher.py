import sys
import asyncio
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output on Windows to avoid UnicodeEncodeError in console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Add project root to sys.path to find 'logic' package
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)
import time
import random
import re
import requests
from playwright.async_api import async_playwright
from logic.supabase_lite import SupabaseLite

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ProductEnricher")

class ProductEnricher:
    """
    Background enricher that scrapes product detail pages to extract EAN and specifications.
    Runs in batches with rate limiting to avoid blocking.
    """
    
    def __init__(self, batch_size=1, delay_between_requests=5):
        self.db = SupabaseLite()
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
        logger.info("ENRICHER VERSION: 2.2 (Robustness + Logging)")
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
        
        logger.info(f"Found {len(products)} products to enrich")
        
        if not products:
            print("No products need enrichment")
            self.update_status(running=False)
            return
        
        user_data_dir = os.path.join(os.getcwd(), "user_data", f"temp_enrich_{int(time.time())}")
        os.makedirs(user_data_dir, exist_ok=True)
        
        async with async_playwright() as p:
            logger.info(f"Launching persistent context in {user_data_dir}...")
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
                        
                        logger.info(f"[{i+1}/{len(products)}] Processing {meli_id}...")
                        
                        # Scrape detail page with resilient fallback
                        details = await self.scrape_product_details(page_for_task, url, meli_id=meli_id)
                        
                        # Update database and log
                        if details and (details.get('ean') or details.get('specs') or details.get('available_quantity') is not None or details.get('item_status')):
                            self.update_product(product['id'], details)
                            
                            ean = details.get('ean', 'N/A')
                            stock = details.get('available_quantity', 0)
                            meta = details.get('metadata', {})
                            seller = meta.get('seller_name', 'Unknown')
                            if meta.get('is_official_store'):
                                seller += " [OFFICIAL]"
                            
                            sold = meta.get('sold_quantity', 0)
                            status_desc = details.get('status_description', '')
                            brand = details.get('specs', {}).get('Marca', 'N/A')
                            category = details.get('metadata', {}).get('category', 'Unknown')
                            
                            # High-Visibility Output
                            item_status = details.get('item_status', 'active')
                            status_icon = "OK" if item_status == "active" else "PAUSED" if item_status == "paused" else "ERR"
                            print(f"  |- Seller: {seller}")
                            print(f"  |- Stock:  {stock} units")
                            print(f"  |- Brand:  {brand} | Category: {category}")
                            print(f"  |- Status: {status_icon} {item_status} ({status_desc if status_desc else 'Publicacion activa'})")
                            print(f"  |- EAN:    {ean} | Sold: {sold} | Cond: {meta.get('condition', 'new')}")
                            
                            self.log_product(meli_id, url, "enriched", ean=ean, stock=stock)
                            self.progress["enriched"] += 1
                        else:
                            print(f"  |- ! {meli_id} - No extra data found")
                            self.log_product(meli_id, url, "no_data")
                        
                        self.progress["processed"] += 1
                        self.update_status()
                        
                    except Exception as e:
                        logger.error(f"  [ERROR] {meli_id}: {e}")
                        print(f"  X {meli_id} Error: {e}")
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
        """Get products that need enrichment using SupabaseLite (requests)."""
        try:
            # Fetch products matched in compliance_audit where ean or brand or seller is missing
            # Only target items that passed the audit (item_status = active)
            endpoint = f"{self.db.url}/rest/v1/meli_listings?select=*&item_status=eq.active"
            # Prioritize those missing critical audit data
            endpoint += "&or=(ean_published.is.null,brand_detected.is.null,seller_name.is.null)"
            
            if limit:
                endpoint += f"&limit={limit}"
                
            response = requests.get(endpoint, headers=self.db.headers)
            response.raise_for_status()
            all_products = response.json()
            
            # Sort locally by last_enriched_at (nulls first -> oldest enriched first)
            all_products.sort(key=lambda x: x.get("last_enriched_at") or "1970-01-01T00:00:00")
            
            return all_products
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            return []
        except Exception as e:
            print(f"Error fetching products: {e}")
            return []
    
    def clean_url(self, url):
        """
        Clean tracking URLs and extract actual product URL.
        Now preserves catalog /p/ links and other valid permalinks.
        """
        if not url or url == 'N/A' or url == 'None':
            return None
            
        import re
        
        # 1. Skip or fix tracking URLs (click1.mercadolibre.com)
        if 'click1.mercadolibre.com' in url or 'mclics' in url:
            mla_match = re.search(r'MLA-?(\d+)', url)
            if mla_match:
                mla_id = mla_match.group(1)
                return f"https://articulo.mercadolibre.com.ar/MLA-{mla_id}"
            return None
        
        # 2. If it's already a valid mercadolibre URL, keep it
        if 'mercadolibre.com.ar' in url:
            # Special check: If it's a catalog redirect, keep it!
            return url
            
        # 3. Last fallback: normalize to standard articulo link
        mla_match = re.search(r'MLA-?(\d+)', url)
        if mla_match:
            mla_id = mla_match.group(1)
            return f"https://articulo.mercadolibre.com.ar/MLA-{mla_id}"
            
        return url
    
    async def scrape_product_details(self, page, url, meli_id=None):
        """
        Scrapes a MELI product page for seller and stock info.
        Uses a fallback mechanism: 1. Permalink -> 2. Catalog (/p/) -> 3. Standard Artículo URL
        """
        urls_to_try = []
        clean_p = self.clean_url(url)
        if clean_p: urls_to_try.append(clean_p)
        
        if meli_id:
            catalog_id = meli_id.replace('MLA', '')
            urls_to_try.append(f"https://www.mercadolibre.com.ar/p/MLA{catalog_id}")
            urls_to_try.append(f"https://articulo.mercadolibre.com.ar/MLA-{catalog_id}")
            
        # Deduplicate while preserving order
        urls_to_try = list(dict.fromkeys(urls_to_try))
        
        details = None
        for attempt_url in urls_to_try:
            details = await self._perform_navigation_and_scrape(page, attempt_url)
            if details and not details.get('is_error'):
                return details
            print(f"  ⚠ Failed to scrap {attempt_url}. Trying next...")
            
        return details

    async def _perform_navigation_and_scrape(self, page, url):
        """Internal logic for a single navigation attempt."""
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
            # Try to navigate with a reasonable timeout
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Check for 404 or page-not-found markers
            if not response or response.status == 404:
                return {"is_error": True, "status": 404}
            
            if await page.locator("text=Parece que esta página no existe").count() > 0:
                return {"is_error": True, "status": 404}
                
            # Bot/Login Wall / Redirected Detection
            if any(p in page.url for p in ["account-verification", "negative_traffic", "login", "auth"]):
                logger.info(f"    ⚠ Redirection detected: {page.url}")
                if "negative_traffic" in page.url or "account-verification" in page.url:
                    details["item_status"] = "paused"
                    return details
                
                print("\n" + "!"*80 + "\n🛑 BLOQUEO/LOGIN: Completa el login/captcha en Chrome y presiona ENTER...")
                await asyncio.get_event_loop().run_in_executor(None, input, "Presiona ENTER para reanudar...")
                return await self._perform_navigation_and_scrape(page, url)
            
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

                        let itemStatus = state?.item?.status || "active";
                        const unavailableMsg = document.querySelector('.ui-pdp-message')?.innerText || "";
                        
                        // Refined: If there's an explicit "Not Available" message, it's not "active" in practice
                        if (unavailableMsg && (unavailableMsg.toLowerCase().includes("no está disponible") || unavailableMsg.toLowerCase().includes("no disponible"))) {
                            itemStatus = "paused"; // Or something visually distinct like "unavailable"
                        }
                        
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
                                is_official_store: !!state?.components?.seller?.official_store_id,
                                category: state?.components?.breadcrumb?.categories?.map(c => c.name).join(' > ') || null
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
                if dom_data.get('item_status'): details['item_status'] = dom_data['item_status']
                if dom_data.get('status_description'): details['status_description'] = dom_data['status_description']

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
                except Exception as e:
                    logger.debug(f"API Fallback failed for {meli_id}: {e}")
            
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
            
            # Brand detection handling
            brand_to_store = details.get('specs', {}).get('brand')
            if brand_to_store:
                update_data['brand_detected'] = brand_to_store
            else:
                update_data['brand_detected'] = 'Unknown'
                
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
                # Fetch current attributes using requests
                endpoint_select = f"{self.db.url}/rest/v1/meli_listings?select=attributes&id=eq.{product_id}"
                try:
                    res_get = requests.get(endpoint_select, headers=self.db.headers)
                    if res_get.ok and res_get.json():
                        current_attrs = res_get.json()[0].get('attributes') or {}
                    else:
                        current_attrs = {}
                except Exception:
                    current_attrs = {}
                
                # Merge ALL specs from details
                if details.get('specs'):
                    for key, value in details['specs'].items():
                        current_attrs[key] = value
                
                # Add description
                if details.get('description'):
                    current_attrs['description_long'] = details['description']
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
                endpoint = f"{self.db.url}/rest/v1/meli_listings?id=eq.{product_id}"
                response = requests.patch(endpoint, json=update_data, headers=self.db.headers)
                response.raise_for_status()
                
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
    print("Delay: Randomized (7-14s) for speed")
    print("Limit:", limit, "products")
    print("=" * 60)
    
    enricher = ProductEnricher(batch_size=batch_size, delay_between_requests=delay)
    asyncio.run(enricher.enrich_products(limit=limit))
