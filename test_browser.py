import asyncio
from playwright.async_api import async_playwright

async def test():
    print("Testing Playwright with native Chrome...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page()
        await page.goto("https://example.com")
        title = await page.title()
        print(f"Success! Page title: {title}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
