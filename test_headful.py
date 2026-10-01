import asyncio
from playwright.async_api import async_playwright

async def test_headful():
    print("[*] Launching headful chrome...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(channel="chrome", headless=False)
            page = await browser.new_page()
            await page.goto("https://www.google.com")
            print("[+] Headful Chrome opened successfully!")
            await asyncio.sleep(5)
            await browser.close()
    except Exception as e:
        print(f"[!] Error launching headful: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_headful())
