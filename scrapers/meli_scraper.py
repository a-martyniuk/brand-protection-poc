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
                
                while True:
                    await page.wait_for_selector(".ui-search-results", timeout=10000)
                    items = await page.query_selector_all(".ui-search-layout__item")
                    
                    for item in items:
                        try:
                            title_el = await item.query_selector(".ui-search-item__title")
                            title = await title_el.inner_text() if title_el else "N/A"
                            
                            price_el = await item.query_selector(".ui-search-price__second-line .price-tag-fraction")
                            price_str = await price_el.inner_text() if price_el else "0"
                            price = float(price_str.replace(".", "").replace(",", "."))
                            
                            link_el = await item.query_selector("a.ui-search-link")
                            link = await link_el.get_attribute("href") if link_el else "N/A"
                            
                            # ID extraction from link or DOM
                            meli_id = link.split("-")[1] if link and "-" in link else "N/A"

                            self.results.append({
                                "id": meli_id,
                                "title": title,
                                "price": price,
                                "url": link
                            })
                        except Exception as e:
                            print(f"Error parsing item: {e}")

                    # Pagination
                    next_button = await page.query_selector(".andes-pagination__button--next a")
                    if next_button:
                        next_url = await next_button.get_attribute("href")
                        print(f"Moving to next page: {next_url}")
                        await page.goto(next_url, wait_until="networkidle")
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
