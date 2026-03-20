import asyncio
import os
import json
import re
import random
from playwright.async_api import async_playwright

class MeliAPIScraper:
    """
    Refactored to Hybrid/Web only due to API blocks (PolicyAgent 403).
    Acts as a drop-in replacement for the API scraper but uses Playwright for everything.
    Includes pagination to scale to 10,000+ items.
    """
    def __init__(self, search_items):
        self.search_items = search_items
        self.results = []
        self.access_token = os.getenv("MELI_ACCESS_TOKEN")

    async def scrape(self):
        print("Starting Scalable Web Scrape (Paginating to 10k items)...")
        
        async with async_playwright() as p:
            user_data_dir = os.path.join(os.getcwd(), "user_data", "manual_session_hotspot")
            os.makedirs(user_data_dir, exist_ok=True)
            
            print(f"Launching persistent context in {user_data_dir} (HEADED MODE)...")
            context = await p.chromium.launch_persistent_context(
                user_data_dir,
                channel="chrome", 
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.pages[0] if context.pages else await context.new_page()
            
            await page.set_extra_http_headers({"Accept-Language": "es-419,es;q=0.9"})
            
            try:
                print("Navigating to home page to establish session...")
                await page.goto("https://www.mercadolibre.com.ar", wait_until="networkidle", timeout=60000)
                await asyncio.sleep(2)
            except Exception:
                pass

            for item in self.search_items:
                query = item.get("product_name", "").replace("Brand: ", "")
                print(f"Searching for: {query}")
                
                try:
                    search_input = await page.wait_for_selector("input.nav-search-input")
                    await search_input.fill("")
                    await search_input.fill(query)
                    await asyncio.sleep(1)
                    await page.keyboard.press("Enter")
                    
                    # Pagination Loop (per brand)
                    pages_to_scrape = 10 # 10 pages * ~50 items = ~500 items per brand
                    for page_num in range(pages_to_scrape):
                        print(f"  Scraping page {page_num + 1} for {query}...")
                        await page.wait_for_load_state("networkidle", timeout=60000)
                        await asyncio.sleep(2)
                        
                        try:
                            await page.wait_for_selector(".ui-search-layout__item, .ui-search-item__title", timeout=15000)
                        except:
                            print(f"    No results or end of list reached.")
                            break
                        
                        # Extract data from current page
                        page_results = await page.evaluate(r"""
                            (categoryName) => {
                                const items = document.querySelectorAll('.ui-search-layout__item, .ui-search-result');
                                let preloadedState = {};
                                try {
                                    const script = Array.from(document.querySelectorAll('script'))
                                        .find(s => s.innerText.includes('window.__PRELOADED_STATE__'));
                                    if (script) {
                                        preloadedState = JSON.parse(script.innerText.split('window.__PRELOADED_STATE__ = ')[1].split(';')[0]);
                                    }
                                } catch(e) {}
                                const stateResults = (preloadedState.results || []);
                                
                                return Array.from(items).map((item, index) => {
                                    const titleEl = item.querySelector('.ui-search-item__title, .poly-component__title, h2');
                                    const priceEl = item.querySelector('.andes-money-amount__fraction');
                                    const linkEl = item.querySelector('a.ui-search-link, a.poly-component__title, a');
                                    const imgEl = item.querySelector('img.ui-search-result-image__element, .poly-component__picture img, img');
                                    const stateItem = stateResults[index] || {};
                                    let mainCategory = categoryName; 
                                    try {
                                        const categoryFilter = (preloadedState.filters || []).find(f => f.id === 'category');
                                        if (categoryFilter && categoryFilter.values && categoryFilter.values.length > 0) {
                                            mainCategory = categoryFilter.values[categoryFilter.values.length - 1].name;
                                        }
                                    } catch(e) {}
                                    let priceText = priceEl ? priceEl.innerText.replace(/\D/g, '') : (stateItem.price ? String(stateItem.price) : '0');
                                    const attributes = {};
                                    const attributeSelectors = ['.ui-search-item__group__element--attributes', '.poly-attributes-list__item', '.ui-search-card-attributes__item', '.poly-component__attributes-list-item'];
                                    for (const selector of attributeSelectors) {
                                        const tagEls = item.querySelectorAll(selector);
                                        if (tagEls.length > 0) {
                                            tagEls.forEach(el => {
                                                const text = el.innerText.trim();
                                                const lowerText = text.toLowerCase();
                                                if (lowerText.includes('marca')) attributes.brand = text.split(':').length > 1 ? text.split(':')[1].trim() : text.replace(/marca/i, '').trim();
                                                if (lowerText.includes('neto') || lowerText.includes('peso') || lowerText.includes('gr') || lowerText.includes('ml')) attributes.weight = text;
                                            });
                                            if (Object.keys(attributes).length > 0) break;
                                        }
                                    }
                                    const seller = stateItem.seller || {};
                                    const reputation = seller.seller_reputation || {};
                                    return {
                                        title: titleEl ? titleEl.innerText : (stateItem.title || 'N/A'),
                                        price_str: priceText,
                                        url: linkEl ? linkEl.href : (stateItem.permalink || 'N/A'),
                                        thumbnail: imgEl ? imgEl.src : (stateItem.thumbnail || null),
                                        seller_id: seller.id || 'N/A',
                                        seller_name: seller.nickname || 'N/A',
                                        is_official_store: !!seller.official_store_id,
                                        official_store_id: seller.official_store_id || null,
                                        seller_reputation: reputation.level_id || 'N/A',
                                        category: mainCategory,
                                        raw_attributes: attributes,
                                        meli_id: stateItem.id || (linkEl ? (linkEl.href.match(/MLA-?(\d+)/) || [null, 'N/A'])[1] : 'N/A')
                                    };
                                });
                            }
                        """, item.get("category", "Uncategorized"))
                        
                        for res in page_results:
                            norm_attrs = self.normalize_attributes(res["title"], res["raw_attributes"])
                            # Clean URL
                            clean_url = res["url"].split('?')[0] if '?' in res["url"] else res["url"]
                            
                            self.results.append({
                                "meli_id": res["meli_id"],
                                "title": res["title"],
                                "price": float(res["price_str"]) if res["price_str"] else 0.0,
                                "url": clean_url,
                                "thumbnail": res["thumbnail"],
                                "category": res["category"],
                                "seller_id": str(res["seller_id"]),
                                "seller_name": res["seller_name"],
                                "is_official_store": res["is_official_store"],
                                "official_store_id": res["official_store_id"],
                                "seller_reputation": res["seller_reputation"],
                                "ean_published": None,
                                "attributes": norm_attrs,
                                "official_product_id": item.get("official_id")
                            })

                        # Pagination: Click "Siguiente"
                        if page_num < pages_to_scrape - 1:
                            try:
                                next_button = await page.query_selector('a.andes-pagination__link[title="Siguiente"], .andes-pagination__button--next a')
                                if next_button:
                                    await next_button.click()
                                    await asyncio.sleep(random.uniform(2, 4))
                                else:
                                    break
                            except:
                                break
                    
                except Exception as e:
                    print(f"  Error scraping {query}: {e}")

            await self.enrich_with_stock(context)
            await context.close()
            
        print(f"Total results collected: {len(self.results)}")
        return self.results

    async def enrich_with_stock(self, context):
        print("Enriching items with stock data via ML API...")
        unique_clean_ids = set()
        id_to_results = {}
        for r in self.results:
            if r.get("meli_id") and r["meli_id"] != "N/A" and "MLA" in r["meli_id"]:
                clean_id = r["meli_id"].replace("-", "")
                unique_clean_ids.add(clean_id)
                if clean_id not in id_to_results: id_to_results[clean_id] = []
                id_to_results[clean_id].append(r)
        
        batch_size = 20
        unique_list = list(unique_clean_ids)
        token = os.environ.get("MELI_ACCESS_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        for i in range(0, len(unique_list), batch_size):
            batch = unique_list[i:i+batch_size]
            url = f"https://api.mercadolibre.com/items?ids={','.join(batch)}"
            try:
                response = await context.request.get(url, headers=headers)
                if response.ok:
                    data = await response.json()
                    for item_data in data:
                        if item_data.get("code") == 200:
                            body = item_data.get("body", {})
                            item_id = body.get("id")
                            stock = body.get("available_quantity", 0)
                            variations = body.get("variations", [])
                            if variations:
                                stock = sum(v.get("available_quantity", 0) for v in variations)
                            if item_id in id_to_results:
                                for res in id_to_results[item_id]:
                                    res["available_quantity"] = stock
            except Exception as e:
                print(f"  Error fetching stock for batch: {e}")
                
        for r in self.results:
            if "available_quantity" not in r: r["available_quantity"] = 0

    def normalize_attributes(self, title, attributes):
        full_text = f"{title} {attributes.get('weight', '')}".lower()
        weight_match = re.search(r'(\d+)\s*(gr|g|kg|ml|l)', full_text)
        if weight_match:
            val = float(weight_match.group(1))
            unit = weight_match.group(2)
            if unit in ['gr', 'g', 'ml']: attributes['net_content'] = val / 1000.0
            else: attributes['net_content'] = val
        if not attributes.get('brand'):
            nutricia_brands = ["nutrilon", "vital", "neocate", "profutura"]
            for b in nutricia_brands:
                if b in title.lower():
                    attributes['brand'] = b.title()
                    break
        return attributes

    def save_results(self, filename="user_data/raw_listings.json"):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4, ensure_ascii=False)
        print(f"Saved {len(self.results)} products to {filename}")
