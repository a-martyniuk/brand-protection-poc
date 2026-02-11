import asyncio
import json
import os
from playwright.async_api import async_playwright

class MeliScraper:
    def __init__(self, base_urls):
        self.base_urls = base_urls
        self.results = []

    async def scrape(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            # Set viewport to be sure we see things
            await page.set_viewport_size({"width": 1280, "height": 800})
            
            # Anti-detection basic header
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            })

            for url in self.base_urls:
                print(f"Scraping: {url}")
                await page.goto(url, wait_until="networkidle")
                
                page_count = 0
                max_pages = 3  # PoC Limit
                while page_count < max_pages:
                    try:
                        await page.wait_for_selector(".ui-search-results", timeout=10000)
                    except:
                        print("No results found or timed out.")
                        break

                    items = await page.query_selector_all(".ui-search-layout__item")
                    print(f"Found {len(items)} items on page {page_count + 1}")
                    
                    # Browser-side extraction for speed and reliability - using raw string for regex
                    page_products = await page.evaluate(r"""
                        () => {
                            const items = document.querySelectorAll('.ui-search-layout__item');
                            return Array.from(items).map(item => {
                                const titleEl = item.querySelector('.ui-search-item__title') || 
                                                item.querySelector('.poly-component__title') ||
                                                item.querySelector('h2');
                                
                                // Price extraction
                                const priceContainer = item.querySelector('.andes-money-amount') || 
                                                       item.querySelector('.ui-search-price__part') ||
                                                       item.querySelector('.poly-price__current');
                                
                                let priceText = '0';
                                if (priceContainer) {
                                    const ariaLabel = priceContainer.getAttribute('aria-label');
                                    if (ariaLabel) {
                                        priceText = ariaLabel.replace(/\D/g, '') || '0';
                                    } 
                                    if (priceText === '0') {
                                        const fractionEl = priceContainer.querySelector('.andes-money-amount__fraction') || 
                                                           priceContainer.querySelector('.ui-search-price__second-line__label') ||
                                                           priceContainer;
                                        priceText = fractionEl.innerText.replace(/\D/g, '') || '0';
                                    }
                                }
                                
                                const linkEl = item.querySelector('.ui-search-link') || 
                                               item.querySelector('.poly-component__title a') || 
                                               item.querySelector('a');
                                const imgEl = item.querySelector('.ui-search-result-image__element') || 
                                              item.querySelector('.poly-component__picture img') ||
                                              item.querySelector('img');
                                
                                // Enhanced Seller extraction
                                let sellerName = 'N/A';
                                const sellerStrategies = [
                                    '.ui-search-item__group__element--seller',
                                    '.poly-component__seller',
                                    '.ui-search-official-store-item__link',
                                    '.ui-search-item__seller-name-link',
                                    '.poly-seller__official-store', // Catalog specific
                                    'a[href*="perfil"]'
                                ];
                                for (const selector of sellerStrategies) {
                                    const el = item.querySelector(selector);
                                    if (el && el.innerText.trim()) {
                                        sellerName = el.innerText.replace(/por\s+/i, '').replace('Vendido ', '').trim();
                                        break;
                                    }
                                }
                                
                                // Enhanced Location extraction
                                let location = 'N/A';
                                const locationStrategies = [
                                    '.ui-search-item__location',
                                    '.poly-component__location',
                                    '.ui-search-item__group__element--location',
                                    '.poly-component__location' // Duplicate but safe
                                ];
                                for (const selector of locationStrategies) {
                                    const el = item.querySelector(selector);
                                    if (el && el.innerText.trim()) {
                                        location = el.innerText.trim();
                                        break;
                                    }
                                }
                                
                                // Last resort: look for any span with poly-box or similar that looks like a location
                                if (location === 'N/A') {
                                    const locEl = Array.from(item.querySelectorAll('span, p')).find(el => 
                                        /capital federal|gba|buenos aires|córdoba|santa fe/i.test(el.innerText)
                                    );
                                    if (locEl) location = locEl.innerText.trim();
                                }

                                return {
                                    title: titleEl ? titleEl.innerText : 'N/A',
                                    price_str: priceText,
                                    url: linkEl ? linkEl.href : 'N/A',
                                    thumbnail: imgEl ? imgEl.src : null,
                                    seller_name: sellerName,
                                    seller_location: location
                                };
                            });
                        }
                    """)
                    
                    print(f"Extracted {len(page_products)} items from page {page_count + 1}")
                    
                    for p in page_products:
                        if p["seller_name"] == "N/A" or p["seller_location"] == "N/A":
                            # print(f"DEBUG: Missing DNA for {p['title']}")
                            pass
                        
                        try:
                            title = p["title"]
                            link = p["url"]
                            price_val = float(p["price_str"].replace(".", "").replace(",", "."))
                            
                            meli_id = "N/A"
                            if link and "MLA" in link:
                                import re
                                match = re.search(r'MLA-?(\d+)', link)
                                if match:
                                    meli_id = f"MLA-{match.group(1)}"

                            self.results.append({
                                "id": meli_id,
                                "title": title,
                                "price": price_val,
                                "url": link,
                                "thumbnail": p.get("thumbnail"),
                                "seller_name": p.get("seller_name"),
                                "seller_location": p.get("seller_location")
                            })
                        except Exception as e:
                            pass

                    page_count += 1
                    await asyncio.sleep(2)
                    
                    next_button = await page.query_selector(".andes-pagination__button--next a")
                    if next_button:
                        next_url = await next_button.get_attribute("href")
                        if next_url and next_url.startswith("http"):
                            print(f"Moving to next page: {next_url}")
                            await page.goto(next_url, wait_until="networkidle")
                        else:
                            break
                    else:
                        break

            await browser.close()
            return self.results

    def save_results(self, filename="d:/Projects/brand-protection-poc/data/raw_products.json"):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4, ensure_ascii=False)
        print(f"Saved {len(self.results)} products to {filename}")

if __name__ == "__main__":
    # Sample URL for testing (iPhone 15 in Argentina)
    test_urls = ["https://listado.mercadolibre.com.ar/iphone-15"]
    scraper = MeliScraper(test_urls)
    asyncio.run(scraper.scrape())
    scraper.save_results()
