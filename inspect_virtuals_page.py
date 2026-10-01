import asyncio
from playwright.async_api import async_playwright

async def inspect_virtuals_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("[*] Navigating to https://www.sportybet.com/ng/virtual/...")
        await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(5)

        # Check for iframes
        frames = page.frames
        print(f"[+] Total frames: {len(frames)}")
        for idx, f in enumerate(frames):
            print(f"  Frame {idx}: name='{f.name}', url='{f.url[:120]}'")

        # Check for tabs or sub-sports (Speedway, Dogs, Horses, etc.)
        buttons = await page.query_selector_all("button, a, .tab, [class*='tab'], [class*='nav']")
        print(f"[+] Found {len(buttons)} navigation elements:")
        for b in buttons:
            txt = (await b.inner_text()).strip()
            href = await b.get_attribute("href") or ""
            if any(k in txt.lower() for k in ["speedway", "bristol", "dog", "horse", "golden", "virtus"]):
                print(f"  Nav item: '{txt}' href='{href}'")

        await page.screenshot(path="sportybet_virtuals_page.png", full_page=True)
        print("[+] Saved sportybet_virtuals_page.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_virtuals_page())
