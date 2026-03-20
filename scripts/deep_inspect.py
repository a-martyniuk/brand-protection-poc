import asyncio
from playwright.async_api import async_playwright
import json
import os

async def deep_inspect():
    user_data_dir = os.path.abspath("user_data/manual_session_hotspot")
    test_url = "https://articulo.mercadolibre.com.ar/MLA-3386240693"
    
    print(f"🚀 Launching browser with session: {user_data_dir}")
    
    async with async_playwright() as p:
        # Launch persistent context to use the user's login
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ignore_default_args=["--enable-automation"],
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = await context.new_page()
        print(f"🔍 Navigating to: {test_url}")
        
        try:
            await page.goto(test_url, wait_until="load", timeout=90000)
            
            # Pause for manual login if needed
            if any(p in page.url for p in ["account-verification", "negative_traffic", "login", "auth"]):
                print("\n" + "!"*80 + "\n🛑 BLOQUEO/LOGIN: Por favor, LOGUEATE en la ventana de Chrome y luego presiona ENTER aquí...")
                await asyncio.get_event_loop().run_in_executor(None, input, "Presiona ENTER para reanudar...")
                await page.goto(test_url, wait_until="load", timeout=90000)
            
            await asyncio.sleep(5) # Extra wait for JS
            
            final_url = page.url
            print(f"📍 Final URL: {final_url}")
            
            # Take a screenshot for visual proof
            screenshot_path = "deep_inspect_screenshot.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot saved to: {screenshot_path}")
            
            # Extract state and metadata
            data = await page.evaluate(r"""
                () => {
                    const state = window.__PRELOADED_STATE__;
                    const html_box = document.querySelector('.ui-pdp-buybox')?.innerHTML || "NOT_FOUND";
                    const html_specs = document.querySelector('.ui-pdp-specs__table')?.innerHTML || "NOT_FOUND";
                    const seller_info = document.querySelector('.ui-pdp-seller__link-container')?.innerText || "NOT_FOUND";
                    
                    return {
                        url: window.location.href,
                        has_preloaded_state: !!state,
                        state_keys: state ? Object.keys(state) : [],
                        initial_state_keys: state?.initialState ? Object.keys(state.initialState) : [],
                        full_state: state,
                        buybox_html_sample: html_box.substring(0, 500),
                        specs_html_sample: html_specs.substring(0, 500),
                        seller_text: seller_info
                    };
                }
            """)
            
            # Save to file
            output_file = "deep_inspect_result.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Inspection complete! Result saved to: {output_file}")
            print(f"   Has Preloaded State: {data['has_preloaded_state']}")
            print(f"   Seller text found: {data['seller_text']}")
            
        except Exception as e:
            print(f"❌ Error during inspection: {e}")
        finally:
            # Keep browser open for a bit for the user to see
            await asyncio.sleep(5)
            await context.close()

if __name__ == "__main__":
    asyncio.run(deep_inspect())
