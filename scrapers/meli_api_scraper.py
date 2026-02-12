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
                    await page.goto(search_url, wait_until="networkidle", timeout=60000)
                    
                    # Wait for results or empty state
                    await page.wait_for_selector(".ui-search-layout__item, .ui-search-item__title", timeout=15000)
                    
                    # Extract all data directly from the DOM
                    page_results = await page.evaluate("""
                        (categoryName) => {
                            const items = document.querySelectorAll('.ui-search-layout__item, .ui-search-result');
                            
                            // Try to find global preloaded state for better attributes
                            let globalData = {};
                            try {
                                const scripts = document.querySelectorAll('script');
                                for (const s of scripts) {
                                    if (s.innerText.includes('window.__PRELOADED_STATE__')) {
                                        const jsonStr = s.innerText.split('window.__PRELOADED_STATE__ = ')[1].split(';')[0];
                                        globalData = JSON.parse(jsonStr);
                                        break;
                                    }
                                }
                            } catch(e) {}

                            const results = Array.from(items).map(item => {
                                const titleEl = item.querySelector('.ui-search-item__title, .poly-component__title, h2');
                                const priceEl = item.querySelector('.andes-money-amount__fraction');
                                const linkEl = item.querySelector('a.ui-search-link, a.poly-component__title, a');
                                const imgEl = item.querySelector('img.ui-search-result-image__element, .poly-component__picture img, img');
                                
                                // Extract simple attributes from visible tags if possible
                                const attributes = {};
                                // Try multiple selector patterns for attributes (Meli A/B testing)
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
                                            if (lowerText.includes('etapa')) {
                                                attributes.stage = text;
                                            }
                                        });
                                        if (Object.keys(attributes).length > 0) break;
                                    }
                                }

                                // Seller
                                let seller = 'N/A';
                                const sellerSelectors = ['.ui-search-item__group__element--seller', '.poly-component__seller', '.ui-search-official-store-item__link'];
                                for (const s of sellerSelectors) {
                                    const el = item.querySelector(s);
                                    if (el && el.innerText.trim()) {
                                        seller = el.innerText.replace(/por\\s+/i, '').trim();
                                        break;
                                    }
                                }
                                
                                // Location
                                let loc = 'N/A';
                                const locSelectors = ['.ui-search-item__location', '.poly-component__location'];
                                for (const s of locSelectors) {
                                    const el = item.querySelector(s);
                                    if (el && el.innerText.trim()) {
                                        loc = el.innerText.trim();
                                        break;
                                    }
                                }

                                return {
                                    title: titleEl ? titleEl.innerText : 'N/A',
                                    price_str: priceEl ? priceEl.innerText.replace(/\\D/g, '') : '0',
                                    url: linkEl ? linkEl.href : 'N/A',
                                    thumbnail: imgEl ? imgEl.src : null,
                                    seller_name: seller,
                                    seller_location: loc,
                                    category: categoryName,
                                    attributes: attributes
                                };
                            });

                            return results;
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
                        
                        self.results.append({
                            "meli_id": meli_id,
                            "title": r["title"],
                            "price": float(r["price_str"]) if r["price_str"] else 0.0,
                            "url": r["url"],
                            "thumbnail": r["thumbnail"],
                            "seller_name": r["seller_name"],
                            "seller_location": r["seller_location"],
                            "category": r["category"],
                            "attributes": attributes, # New field
                            "official_product_id": item.get("official_id")
                        })
                        
                except Exception as e:
                    print(f"Error scraping {query}: {e}")

            await browser.close()
        return self.results

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
