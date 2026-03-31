import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating...")
        await page.goto("https://listado.mercadolibre.com.ar/infatrini", wait_until="networkidle")
        
        # Get the HTML of the first 3 items
        items = await page.evaluate(r'''
            () => {
                const els = document.querySelectorAll('.ui-search-layout__item, .poly-card');
                return Array.from(els).slice(0, 3).map(el => el.outerHTML);
            }
        ''')
        
        for i, html in enumerate(items):
            with open(f"./scripts/item_{i}.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Saved ./scripts/item_{i}.html")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
