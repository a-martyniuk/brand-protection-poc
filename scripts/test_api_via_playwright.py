import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Navigate to the API URL
        await page.goto("https://api.mercadolibre.com/sites/MLA/search?q=Nutrilon")
        
        # Get the page text content (which should be JSON)
        content = await page.content() # This gets HTML, but for JSON response it's usually inside <pre> or just text
        text = await page.inner_text("body")
        
        print(text[:1000]) # Print first 1000 chars
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
