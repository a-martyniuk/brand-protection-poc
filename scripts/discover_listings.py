import os
import sys
import asyncio
import random
import re
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Add project root to sys.path to find 'logic' package
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from logic.supabase_lite import SupabaseLite
from logic.constants import NUTRICIA_BRANDS

# Load environment variables
load_dotenv()

class MeliBrowserDiscovery:
    """
    Discovery of MercadoLibre listings using Playwright (Browser-Based)
    to bypass API limits and mimic user behavior.
    """
    
    def __init__(self, pages_per_query=2):
        self.db = SupabaseLite()
        self.pages_per_query = pages_per_query
        self.user_data_dir = os.path.join(os.getcwd(), "user_data", "discovery_session")
        os.makedirs(self.user_data_dir, exist_ok=True)
        
        # Extended keywords from nomenclature exceptions
        self.extra_keywords = [
            "Bifidosa", "Pepti", "Neocate", "Lophlex", "Souvenaid", 
            "Anamix", "Cubitan", "HMO", "Prosyneo", "Fortifit"
        ]

    async def get_search_queries(self):
        """Generates the list of keywords to search for."""
        try:
            products = self.db.get_master_products()
            brands = set(p.get('brand') for p in products if p.get('brand'))
            all_queries = set(list(brands) + NUTRICIA_BRANDS + self.extra_keywords)
            return sorted([q for q in all_queries if q])
        except Exception:
            # Fallback if DB fetch fails
            return sorted(set(NUTRICIA_BRANDS + self.extra_keywords))

    async def run_discovery(self):
        queries = await self.get_search_queries()
        print(f"🚀 Starting Browser Discovery for {len(queries)} queries...")
        
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                self.user_data_dir,
                channel="chrome",
                headless=False, # Headed mode as requested/preferred for stability
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            await page.set_extra_http_headers({"Accept-Language": "es-419,es;q=0.9"})
            
            # Initial home navigation
            try:
                await page.goto("https://www.mercadolibre.com.ar", wait_until="networkidle", timeout=60000)
                await asyncio.sleep(2)
            except Exception:
                pass

            total_upserted = 0
            for i, query in enumerate(queries):
                print(f"[{i+1}/{len(queries)}] Searching: '{query}'...")
                
                try:
                    # Perform search via search bar
                    search_input = await page.wait_for_selector("input.nav-search-input")
                    await search_input.fill("")
                    await search_input.fill(query)
                    await asyncio.sleep(1)
                    await page.keyboard.press("Enter")
                    
                    # Pagination Loop
                    for page_num in range(self.pages_per_query):
                        await page.wait_for_load_state("networkidle", timeout=30000)
                        await asyncio.sleep(2)
                        
                        try:
                            await page.wait_for_selector(".ui-search-layout__item, .ui-search-item__title", timeout=15000)
                        except:
                            print(f"    No results for page {page_num + 1}")
                            break
                        
                        # Extract data
                        items_data = await page.evaluate(r"""
                            () => {
                                // 1. Try to find Category ID from the page state
                                let categoryId = 'N/A';
                                try {
                                    if (window.__PRELOADED_STATE__) {
                                        categoryId = window.__PRELOADED_STATE__.initialState?.components?.breadcrumb?.categories?.[window.__PRELOADED_STATE__.initialState.components.breadcrumb.categories.length - 1]?.id || 'N/A';
                                    }
                                } catch (e) {}

                                const els = document.querySelectorAll('.ui-search-layout__item, .ui-search-result, .poly-card');
                                return Array.from(els).map(el => {
                                    const titleEl = el.querySelector('.ui-search-item__title, .poly-component__title, h2');
                                    const priceEl = el.querySelector('.andes-money-amount__fraction');
                                    const linkEl = el.querySelector('a.ui-search-link, a.poly-component__title, a');
                                    const imgEl = el.querySelector('img.ui-search-result-image__element, .poly-component__picture img, img');
                                    
                                    // New fields
                                    const sellerEl = el.querySelector('.poly-component__seller, .ui-search-official-store-label');
                                    const salesEl = el.querySelector('.poly-component__sales, .poly-sales, .ui-search-item__group__element--shipping'); // Sometimes sales are near shipping
                                    const fullEl = el.querySelector('.ui-search-item__fulfillment, .poly-component__shipping');
                                    
                                    return {
                                        title: titleEl ? titleEl.innerText : 'N/A',
                                        price_str: priceEl ? priceEl.innerText.replace(/\D/g, '') : '0',
                                        url: linkEl ? linkEl.href : 'N/A',
                                        thumbnail: imgEl ? imgEl.src : null,
                                        meli_id: linkEl ? (linkEl.href.match(/MLA-?(\d+)/) || [null, 'N/A'])[1] : 'N/A',
                                        
                                        // Super Scraper fields
                                        category_id: categoryId,
                                        seller_name: sellerEl ? sellerEl.innerText : 'N/A',
                                        sold_quantity_str: salesEl ? salesEl.innerText : null,
                                        is_full: !!(fullEl && fullEl.innerText.includes('FULL')),
                                        is_official_store: !!el.querySelector('.ui-search-official-store-label, .poly-component__seller') // Simple heuristic
                                    };
                                });
                            }
                        """)
                        
                        listings = []
                        for res in items_data:
                            if res["meli_id"] == "N/A": continue
                            
                            listings.append({
                                "meli_id": f"MLA{res['meli_id']}" if not res['meli_id'].startswith('MLA') else res['meli_id'],
                                "title": res["title"],
                                "price": float(res["price_str"]) if res["price_str"] else 0.0,
                                "url": res["url"].split('?')[0],
                                "thumbnail": res["thumbnail"],
                                "search_keyword": query,
                                "last_scraped_at": datetime.now().isoformat(),
                                
                                # Super Scraper fields
                                "category_id": res["category_id"],
                                "category_name": res["category_id"], # Placeholder for now
                                "seller_name": res["seller_name"],
                                "sold_quantity_str": res["sold_quantity_str"],
                                "is_full": res["is_full"],
                                "is_official_store": res["is_official_store"]
                            })
                            
                        if listings:
                            self.db.upsert_meli_listings(listings)
                            total_upserted += len(listings)
                            print(f"    ✓ Page {page_num + 1} - Upserted {len(listings)} items")
                        
                        # Next Page Click
                        if page_num < self.pages_per_query - 1:
                            next_btn = await page.query_selector('a.andes-pagination__link[title="Siguiente"], .andes-pagination__button--next a')
                            if next_btn:
                                await next_btn.click()
                                await asyncio.sleep(random.uniform(2, 4))
                            else:
                                break
                                
                except Exception as e:
                    print(f"  ✗ Error searching '{query}': {e}")
                
                # Cooldown between queries
                await asyncio.sleep(random.uniform(3, 6))
            
            await context.close()
            print("\n" + "="*50)
            print(f"✓ Discovery Complete! Total results: {total_upserted}")
            print("="*50)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Meli Browser Discovery")
    parser.add_argument("--queries", type=str, help="Comma separated queries to search")
    parser.add_argument("--pages", type=int, default=2, help="Pages per query")
    args = parser.parse_args()
    
    discovery = MeliBrowserDiscovery(pages_per_query=args.pages)
    
    if args.queries:
        targeted_queries = [q.strip() for q in args.queries.split(",")]
        # Override the search_queries method for this run
        async def get_targeted_queries():
            return targeted_queries
        discovery.get_search_queries = get_targeted_queries
        
    asyncio.run(discovery.run_discovery())
