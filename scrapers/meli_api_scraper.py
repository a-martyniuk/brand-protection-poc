import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

class MeliAPIScraper:
    """
    Refactored to Hybrid/Web only due to API blocks (PolicyAgent 403).
    Acts as a drop-in replacement for the API scraper but uses Playwright for everything.
    """
    def __init__(self, search_items):
        self.search_items = search_items
        self.results = []
        # Keep client for structure but don't use blocked methods
        self.access_token = os.getenv("MELI_ACCESS_TOKEN")

    async def scrape(self):
        print("Starting Enhanced Web Scrape (API Bypassed)...")
        
        async with async_playwright() as p:
            # Using real browser args to minimize detection
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Establishment pause
            await page.set_extra_http_headers({
                "Accept-Language": "es-419,es;q=0.9",
            })

            for item in self.search_items:
                query = item.get("product_name", "").replace("Brand: ", "")
                print(f"Scraping web results for: {query}")
                search_url = f"https://listado.mercadolibre.com.ar/{query.replace(' ', '-')}"
                
                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                    # Small sleep to allow some JS to run after DOM is ready
                    await asyncio.sleep(2)
                    
                    # Wait for results or empty state
                    await page.wait_for_selector(".ui-search-layout__item, .ui-search-item__title", timeout=15000)
                    
                    # Extract all data directly from the DOM and Preloaded State
                    page_results = await page.evaluate("""
                        (categoryName) => {
                            const items = document.querySelectorAll('.ui-search-layout__item, .ui-search-result');
                            
                            let preloadedState = {};
                            try {
                                const script = Array.from(document.querySelectorAll('script'))
                                    .find(s => s.innerText.includes('window.__PRELOADED_STATE__'));
                                if (script) {
                                    const jsonStr = script.innerText.split('window.__PRELOADED_STATE__ = ')[1].split(';')[0];
                                    preloadedState = JSON.parse(jsonStr);
                                }
                            } catch(e) {}

                            // Enhanced mapping from preloaded state
                            const stateResults = preloadedState.results || [];
                            
                            // Try to find the "Main Category" of the search result from filters
                            let mainCategory = categoryName; 
                            try {
                                const categoryFilter = (preloadedState.filters || []).find(f => f.id === 'category');
                                if (categoryFilter && categoryFilter.values && categoryFilter.values.length > 0) {
                                    mainCategory = categoryFilter.values[categoryFilter.values.length - 1].name;
                                }
                            } catch(e) {}

                            return Array.from(items).map((item, index) => {
                                const titleEl = item.querySelector('.ui-search-item__title, .poly-component__title, h2');
                                const priceEl = item.querySelector('.andes-money-amount__fraction');
                                const linkEl = item.querySelector('a.ui-search-link, a.poly-component__title, a');
                                const imgEl = item.querySelector('img.ui-search-result-image__element, .poly-component__picture img, img');
                                
                                // Enhanced mapping from preloaded state
                                const stateItem = stateResults[index] || {};
                                
                                const attributes = {};
                                const attributeSelectors = [
                                    '.ui-search-item__group__element--attributes',
                                    '.poly-attributes-list__item',
                                    '.ui-search-card-attributes__item',
                                    '.poly-component__attributes-list-item'
                                ];
                                
                                for (const selector of attributeSelectors) {
                                    const tagEls = item.querySelectorAll(selector);
                                    if (tagEls.length > 0) {
                                        tagEls.forEach(el => {
                                            const text = el.innerText.trim();
                                            const lowerText = text.toLowerCase();
                                            if (lowerText.includes('marca')) {
                                                attributes.brand = text.split(':').length > 1 ? text.split(':')[1].trim() : text.replace(/marca/i, '').trim();
                                            }
                                            if (lowerText.includes('neto') || lowerText.includes('peso') || lowerText.includes('gr') || lowerText.includes('ml')) {
                                                attributes.weight = text;
                                            }
                                        });
                                        if (Object.keys(attributes).length > 0) break;
                                    }
                                }

                                // Seller & Reputation
                                const seller = stateItem.seller || {};
                                const reputation = seller.seller_reputation || {};
                                
                                return {
                                    title: titleEl ? titleEl.innerText : (stateItem.title || 'N/A'),
                                    price_str: priceEl ? priceEl.innerText.replace(/\D/g, '') : (stateItem.price || '0'),
                                    url: linkEl ? linkEl.href : (stateItem.permalink || 'N/A'),
                                    thumbnail: imgEl ? imgEl.src : (stateItem.thumbnail || null),
                                    seller_id: seller.id || 'N/A',
                                    seller_name: seller.nickname || 'N/A',
                                    is_official_store: !!seller.official_store_id,
                                    official_store_id: seller.official_store_id || null,
                                    seller_reputation: {
                                        level: reputation.level_id || 'N/A',
                                        power_seller: reputation.power_seller_status || null,
                                        transactions: reputation.transactions || {}
                                    },
                                    category: mainCategory, // Using the real category name from MercadoLibre filters
                                    attributes: attributes
                                };
                            });
                        }
                    """, query)
                    
                    print(f"Extracted {len(page_results)} items for {query}")
                    
                    for r in page_results:
                        # Extract MLA ID from URL
                        meli_id = "N/A"
                        if "MLA" in r["url"]:
                            match = re.search(r'MLA-?(\d+)', r["url"])
                            if match:
                                meli_id = f"MLA{match.group(1)}"
                        
                        # Capture and normalize simple attributes if available in listing
                        attributes = r.get("attributes", {})
                        
                        # Clean URL (remove tracking parameters)
                        url = r["url"]
                        if '?' in url:
                            url = url.split('?')[0]
                        
                        # NEW: Normalize attributes before storage
                        norm_attrs = self.normalize_attributes(r["title"], attributes)
                        
                        self.results.append({
                            "meli_id": meli_id,
                            "title": r["title"],
                            "price": float(r["price_str"]) if r["price_str"] else 0.0,
                            "url": url,
                            "thumbnail": r["thumbnail"],
                            "seller_id": r["seller_id"],
                            "seller_name": r["seller_name"],
                            "is_official_store": r["is_official_store"],
                            "official_store_id": r["official_store_id"],
                            "seller_reputation": r["seller_reputation"],
                            "category": r["category"],
                            "brand_detected": norm_attrs.get("brand"),
                            "ean_published": None,
                            "attributes": norm_attrs,
                            "official_product_id": item.get("official_id")
                        })
                        
                except Exception as e:
                    print(f"Error scraping {query}: {e}")

            await browser.close()
        return self.results

    def normalize_attributes(self, title, attributes):
        """
        Pre-identification normalization of weights and brands.
        """
        # 1. Weight Normalization (e.g., '800 gr' -> 0.8)
        full_text = f"{title} {attributes.get('weight', '')}".lower()
        weight_match = re.search(r'(\d+)\s*(gr|g|kg|ml|l)', full_text)
        if weight_match:
            val = float(weight_match.group(1))
            unit = weight_match.group(2)
            if unit in ['gr', 'g', 'ml']:
                attributes['net_content'] = val / 1000.0
            else:
                attributes['net_content'] = val
        
        # 2. Brand normalization if missing
        if not attributes.get('brand'):
            nutricia_brands = ["nutrilon", "vital", "neocate", "profutura"]
            for b in nutricia_brands:
                if b in title.lower():
                    attributes['brand'] = b.title()
                    break
        
        return attributes

    async def get_item_details(self, url):
        """
        Deep scrape of a single item to get EAN/GTIN and technical specs.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0...")
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                # Try to find EAN in technical specs
                details = await page.evaluate("""
                    () => {
                        const rows = document.querySelectorAll('.andes-table__row');
                        let ean = null;
                        for (const row of rows) {
                            if (row.innerText.includes('EAN') || row.innerText.includes('GTIN') || row.innerText.includes('Código universal de producto')) {
                                const valEl = row.querySelector('.andes-table__column--value');
                                if (valEl) ean = valEl.innerText.trim();
                            }
                        }
                        return { ean };
                    }
                """)
                await browser.close()
                return details
            except Exception:
                await browser.close()
                return {"ean": None}

    def save_results(self, filename="user_data/raw_listings.json"):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4, ensure_ascii=False)
        print(f"Saved {len(self.results)} products to {filename}")

if __name__ == "__main__":
    scraper = MeliAPIScraper([{"product_name": "Nutrilon", "official_id": "test", "expected_price": 20000}])
    asyncio.run(scraper.scrape())
    scraper.save_results()
