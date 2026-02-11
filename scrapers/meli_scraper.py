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
                    
                    # Browser-side extraction for speed and reliability
                    page_products = await page.evaluate("""
                        () => {
                            const items = document.querySelectorAll('.ui-search-layout__item');
                            return Array.from(items).map(item => {
                                const imgEl = item.querySelector('.ui-search-result-image__element') || 
                                              item.querySelector('.poly-component__picture') ||
                                              item.querySelector('img');
                                const locationEl = item.querySelector('.ui-search-item__location') ||
                                                   item.querySelector('.poly-component__location');

                                return {
                                    title: titleEl ? titleEl.innerText : 'N/A',
                                    price_str: priceEl ? priceEl.innerText : '0',
                                    url: linkEl ? linkEl.href : 'N/A',
                                    thumbnail: imgEl ? imgEl.src : null,
                                    seller_name: sellerEl ? sellerEl.innerText : 'Generic Seller',
                                    seller_location: locationEl ? locationEl.innerText : 'Location N/A'
                                };
                            });
                        }
                    """)
                    
                    print(f"Extracted {len(page_products)} items from page {page_count + 1}")
                    
                    for p in page_products:
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
