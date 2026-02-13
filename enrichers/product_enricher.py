import asyncio
import os
import json
from datetime import datetime
from playwright.async_api import async_playwright
from logic.supabase_handler import SupabaseHandler
import time

class ProductEnricher:
    """
    Background enricher that scrapes product detail pages to extract EAN and specifications.
    Runs in batches with rate limiting to avoid blocking.
    """
    
    def __init__(self, batch_size=15, delay_between_requests=3):
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
        
    def update_status(self, **kwargs):
        """Update status file with current progress."""
        self.progress.update(kwargs)
        self.progress["last_update"] = datetime.now().isoformat()
        
        with open(self.status_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def log_product(self, meli_id, url, status, ean=None, error=None):
        """Log individual product processing."""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "meli_id": meli_id,
            "url": url,
            "status": status,
            "ean": ean,
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
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            for i, product in enumerate(products):
                try:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    meli_id = product['meli_id']
                    url = product['url']
                    
                    # Update current status
                    self.update_status(
                        current_product={
                            "meli_id": meli_id,
                            "title": product['title'][:50],
                            "url": url,
                            "timestamp": timestamp
                        },
                        processed=i
                    )
                    
                    print(f"\n[{timestamp}] [{i+1}/{len(products)}] {meli_id}")
                    print(f"  📄 {product['title'][:60]}...")
                    print(f"  🔗 {url[:80]}...")
                    
                    # Scrape detail page
                    details = await self.scrape_product_details(page, url)
                    
                    # Update database and log
                    if details and (details.get('ean') or details.get('specs')):
                        self.update_product(product['id'], details)
                        ean = details.get('ean', 'N/A')
                        print(f"  ✓ Enriched - EAN: {ean}")
                        
                        self.log_product(meli_id, url, "enriched", ean=ean)
                        self.progress["enriched"] += 1
                    else:
                        print(f"  ⚠ No additional data found")
                        self.log_product(meli_id, url, "no_data")
                    
                    # Rate limiting
                    if (i + 1) % self.batch_size == 0:
                        print(f"\n📦 Batch {(i+1)//self.batch_size} complete. Sleeping {self.delay * 2}s...")
                        await asyncio.sleep(self.delay * 2)
                    else:
                        await asyncio.sleep(self.delay)
                        
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    self.log_product(meli_id, url, "failed", error=str(e))
                    self.progress["failed"] += 1
                    continue
                finally:
                    self.progress["processed"] = i + 1
                    self.update_status()
            
            await browser.close()
        
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
        
        Returns:
            List of products needing enrichment
        """
        try:
            # Get products without EAN or without brand_detected
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
    
    def clean_url(self, url):
        """
        Clean tracking URLs and extract actual product URL.
        """
        import re
        
        # Skip tracking URLs (click1.mercadolibre.com)
        if 'click1.mercadolibre.com' in url or 'mclics' in url:
            # Try to extract MLA ID and construct clean URL
            mla_match = re.search(r'MLA\d+', url)
            if mla_match:
                mla_id = mla_match.group(0)
                return f"https://www.mercadolibre.com.ar/p/{mla_id}"
        
        # Remove tracking parameters
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
            dict with 'ean' and 'specs' keys
        """
        try:
            # Clean URL first
            clean_url = self.clean_url(url)
            
            await page.goto(clean_url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for specs table to load (increased timeout)
            await page.wait_for_selector('.andes-table__row, .ui-pdp-specs__table__row', timeout=30000)
            
            # Extract EAN, specs and description
            details = await page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('.andes-table__row, .ui-pdp-specs__table__row');
                    let ean = null;
                    let specs = {};
                    
                    // Extract All Specs
                    for (const row of rows) {
                        const labelEl = row.querySelector('.andes-table__column--label, th');
                        const valueEl = row.querySelector('.andes-table__column--value, td');
                        
                        if (labelEl && valueEl) {
                            const label = labelEl.innerText.trim();
                            const value = valueEl.innerText.trim();
                            const labelLower = label.toLowerCase();
                            
                            // Store raw spec
                            specs[label] = value;
                            
                            // Normalize key fields for easier access
                            // EAN / GTIN
                            if (labelLower.includes('ean') || labelLower.includes('gtin') || labelLower.includes('código universal')) {
                                ean = value;
                            }
                            
                            // Units per pack
                            if (labelLower.includes('unidades por pack') || labelLower.includes('unidades por envase') || labelLower.includes('cantidad de unidades')) {
                                specs.units_per_pack = value;
                            }
                            
                            // Substance / Type
                            if (labelLower.includes('tipo de leche') || labelLower.includes('tipo de suplemento') || labelLower.includes('sustancia') || labelLower.includes('tipo de producto')) {
                                specs.substance = value;
                            }
                            
                            // Weight / Volume
                            if (labelLower.includes('peso neto') || labelLower.includes('contenido neto') || labelLower.includes('volumen')) {
                                specs.net_content = value;
                            }
                            
                            // Stage / Age
                            if (labelLower.includes('etapa') || labelLower.includes('edad mínima') || labelLower.includes('edad recomendada')) {
                                specs.stage = value;
                            }
                        }
                    }

                    // Extract Description
                    const descEl = document.querySelector('.ui-pdp-description__content');
                    const description = descEl ? descEl.innerText.trim() : null;
                    
                    return { ean, specs, description };
                }
            """)
            
            return details
            
        except Exception as e:
            print(f"    Error scraping {url}: {e}")
            return None
    
    def update_product(self, product_id, details):
        """
        Update product with enriched data.
        
        Args:
            product_id: UUID of product in database
            details: dict with 'ean' and 'specs' keys
        """
        try:
            update_data = {}
            
            if details.get('ean'):
                update_data['ean_published'] = details['ean']
            
            if details.get('specs', {}).get('brand'):
                update_data['brand_detected'] = details['specs']['brand']
            
            # Update attributes with all specs and description
            if details.get('specs') or details.get('description'):
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
                
                update_data['attributes'] = current_attrs
            
            if update_data:
                self.db.supabase.table("meli_listings").update(update_data).eq("id", product_id).execute()
                
        except Exception as e:
            print(f"    Error updating product: {e}")

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    delay = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    print("=" * 60)
    print("PRODUCT ENRICHER - Background Deep Scraping")
    print("=" * 60)
    print(f"Batch size: {batch_size}")
    print(f"Delay between requests: {delay}s")
    if limit:
        print(f"Limit: {limit} products")
    print("=" * 60)
    
    enricher = ProductEnricher(batch_size=batch_size, delay_between_requests=delay)
    asyncio.run(enricher.enrich_products(limit=limit))
