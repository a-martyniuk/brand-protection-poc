import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

class MeliScraper:
    def __init__(self, search_items):
        """
        :param search_items: List of dictionaries, each containing:
            - url: The search URL
            - official_id: UUID of the official product
            - expected_price: The official list price (decimal)
            - product_name: Name for logging
        """
        self.search_items = search_items
        self.results = []

    async def scrape(self):
        print("Initializing Playwright...")
        async with async_playwright() as p:
            print("Launching browser with persistent context...")
            user_data_dir = os.path.join(os.getcwd(), "user_data")
            # Create user data dir if it doesn't exist
            os.makedirs(user_data_dir, exist_ok=True)
            
            context = await p.chromium.launch_persistent_context(
                user_data_dir,
                channel="chrome", # Try using real Chrome to bypass bot detection
                headless=True,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled"] 
            )
            
            page = context.pages[0] if context.pages else await context.new_page()

            # Anti-detection basic header - context already sets UA, but let's be safe
            await page.set_extra_http_headers({
                "Accept-Language": "es-419,es;q=0.9",
                "Referer": "https://www.google.com/"
            })

            print(f"Starting to scrape {len(self.search_items)} items...")
            
            # Navigate to home page first to establish session
            try:
                print("Navigating to home page...")
                await page.goto("https://www.mercadolibre.com.ar", wait_until="networkidle", timeout=60000)
                await asyncio.sleep(2) # mimic user pause
            except Exception as e:
                print(f"Error loading home page: {e}")
                return []

            for item in self.search_items:
                # Extract query from URL or use product name if reasonable
                # URL format: .../query
                query = item["url"].split("/")[-1].replace("-", " ")
                print(f"Searching for: {query}")
                
                try:
                    # Type in search bar
                    search_input = await page.wait_for_selector("input.nav-search-input")
                    await search_input.fill("") # Clear
                    await search_input.fill(query)
                    await page.keyboard.press("Enter")
                    
                    # Wait for results or 'no results'
                    await page.wait_for_load_state("networkidle")
                except Exception as e:
                    print(f"Error performing search for {query}: {e}")
                    # DEBUG: detailed failure analysis
                    screenshot_path = f"c:/Users/Martyniuk-Ntbk-Gmr/AppData/Local/Temp/debug_meli_search_fail_{query}.png"
                    await page.screenshot(path=screenshot_path)
                    print(f"Saved debug screenshot to {screenshot_path}")
                    continue
                
                page_count = 0
                max_pages = 2  # PoC Limit per product
                
                while page_count < max_pages:
                    try:
                        # Wait for either results or "no matches" message
                        # .ui-search-results is for grid/list
                        # sometimes it's .ui-search-layout
                        await page.wait_for_selector(".ui-search-layout__item", timeout=10000)
                    except:
                        print("No results found or timed out.")
                        # DEBUG: detailed failure analysis
                        screenshot_path = f"c:/Users/Martyniuk-Ntbk-Gmr/AppData/Local/Temp/debug_meli_{item['product_name'].replace(' ', '_')}.png"
                        await page.screenshot(path=screenshot_path)
                        print(f"Saved debug screenshot to {screenshot_path}")
                        
                        html_path = f"c:/Users/Martyniuk-Ntbk-Gmr/AppData/Local/Temp/debug_meli_{item['product_name'].replace(' ', '_')}.html"
                        with open(html_path, "w", encoding="utf-8") as f:
                            f.write(await page.content())
                        print(f"Saved debug HTML to {html_path}")
                        break
                    
                    items = await page.query_selector_all(".ui-search-layout__item")
                    # print(f"Found {len(items)} items on page {page_count + 1}")
                    
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
                    
                    # print(f"Extracted {len(page_products)} items from page {page_count + 1}")
                    
                    for p in page_products:
                        if p["seller_name"] == "N/A" or p["seller_location"] == "N/A":
                            pass
                        
                        try:
                            title = p["title"]
                            link = p["url"]
                            price_val = float(p["price_str"].replace(".", "").replace(",", "."))
                            
                            meli_id = "N/A"
                            if link and "MLA" in link:
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
                                "seller_location": p.get("seller_location"),
                                # Context fields
                                "official_product_id": item.get("official_id"),
                                "official_expected_price": item.get("expected_price")
                            })
                        except Exception as e:
                            pass

                    page_count += 1
                    await asyncio.sleep(2)
                    
                    # Pagination Logic
                    next_button = await page.query_selector(".andes-pagination__button--next a")
                    if next_button:
                        next_url = await next_button.get_attribute("href")
                        if next_url and next_url.startswith("http"):
                            # print(f"Moving to next page: {next_url}")
                            await page.goto(next_url, wait_until="networkidle")
                        else:
                            break
                    else:
                        break
            
            await browser.close()
            return self.results

    def save_results(self, filename="c:/Users/Martyniuk-Ntbk-Gmr/AppData/Local/Temp/raw_products.json"):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4, ensure_ascii=False)
        print(f"Saved {len(self.results)} products to {filename}")

if __name__ == "__main__":
    # Test with structured item
    test_items = [{
        "url": "https://listado.mercadolibre.com.ar/iphone-15",
        "official_id": "test-uuid",
        "expected_price": 1000000,
        "product_name": "iPhone 15"
    }]
    scraper = MeliScraper(test_items)
    asyncio.run(scraper.scrape())
    scraper.save_results()
