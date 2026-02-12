import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Launching...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        print("Browser launched.")
        page = await browser.new_page()
        print("Page created.")
        await page.goto("https://www.google.com")
        print("Navigated to Google.")
        title = await page.title()
        print(f"Title: {title}")
        await browser.close()
        print("Closed.")

if __name__ == "__main__":
    asyncio.run(main())
