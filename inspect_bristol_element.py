import asyncio
import os
from playwright.async_api import async_playwright

AUTH_PATH = os.path.abspath("auth.json")

async def inspect_bristol_element():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=["--mute-audio"])
        context = await browser.new_context(storage_state=AUTH_PATH, viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        await page.route("**/*", lambda route: route.abort() if any(x in route.request.url.lower() for x in [".mp4", ".webm", ".m3u8", ".ts", ".mp3", "video"]) else route.continue_())
        await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="domcontentloaded", timeout=60000)

        iframe_handle = await page.wait_for_selector("iframe", timeout=35000)
        game_frame = await iframe_handle.content_frame()
        await game_frame.wait_for_selector(".nav-item, a, button", timeout=30000)

        # Click Speedway
        speedway_el = await game_frame.wait_for_selector("a:has-text('Speedway'), [title*='Speedway'], span:has-text('Speedway')", timeout=15000)
        await speedway_el.click()
        await asyncio.sleep(2)

        # Inspect Bristol elements
        bristol_links = await game_frame.query_selector_all("a:has-text('Bristol'), [href*='23100'], [title*='Bristol']")
        print(f"Found {len(bristol_links)} Bristol links:")
        for idx, bl in enumerate(bristol_links):
            html = await bl.evaluate("el => el.outerHTML")
            href = await bl.get_attribute("href")
            print(f"Link {idx}: href='{href}' html={html}")

            # Click it!
            print(f"Clicking Bristol link {idx}...")
            await bl.click()
            await asyncio.sleep(4)

        # Check if URL changed or market panels appeared
        print(f"Game Frame URL after clicking: {game_frame.url}")
        panels = await game_frame.query_selector_all(".market.open")
        print(f"Open market panels: {len(panels)}")

        await page.screenshot(path="bristol_clicked_verified.png", full_page=True)
        print("[+] Saved bristol_clicked_verified.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_bristol_element())
