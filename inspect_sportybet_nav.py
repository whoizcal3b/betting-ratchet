import asyncio
import os
from playwright.async_api import async_playwright

async def inspect_sportybet_nav():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("[*] Loading sportybet.com/ng/ to inspect Virtuals navigation...")
        await page.goto("https://www.sportybet.com/ng/", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(5)

        # Look for links with "virtual" in text or href
        links = await page.query_selector_all("a")
        virtual_links = []
        for l in links:
            txt = (await l.inner_text()).strip()
            href = await l.get_attribute("href") or ""
            if any(k in txt.lower() or k in href.lower() for k in ["virtual", "speedway", "instant", "golden"]):
                virtual_links.append({"text": txt, "href": href})
                print(f"Found link: text='{txt}' | href='{href}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_sportybet_nav())
