import asyncio
import os
from playwright.async_api import async_playwright

USER_DATA = os.path.abspath("chrome_user_data")

async def test_visible():
    print(f"[*] Launching persistent Chrome with profile in {USER_DATA}...")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            USER_DATA,
            channel="chrome",
            headless=False,
            args=[
                "--start-maximized",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        print("[+] Chrome launched! Navigating to sportybet...")
        await page.goto("https://www.sportybet.com/ng/", wait_until="domcontentloaded", timeout=45000)
        print("[+] Navigated to SportyBet! Keeping window open for 60 seconds...")
        for i in range(6):
            await asyncio.sleep(10)
            print(f"[*] Window still open ({ (i+1)*10 }s)...")
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_visible())
