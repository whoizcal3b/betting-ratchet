import asyncio
import os
from playwright.async_api import async_playwright

AUTH_PATH = os.path.abspath("auth.json")

async def test_hash_routing():
    print("[*] Testing direct hash route change to Bristol...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=["--mute-audio"])
        context = await browser.new_context(storage_state=AUTH_PATH, viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        await page.route("**/*", lambda route: route.abort() if any(x in route.request.url.lower() for x in [".mp4", ".webm", ".m3u8", ".ts", ".mp3", "video"]) else route.continue_())
        await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="domcontentloaded", timeout=60000)

        iframe_handle = await page.wait_for_selector("iframe", timeout=35000)
        game_frame = await iframe_handle.content_frame()
        await game_frame.wait_for_selector(".nav-item, a, button", timeout=30000)

        print("[*] Setting location.hash to #/scheduled/speedway/playlist/23100...")
        await game_frame.evaluate("() => { window.location.hash = '#/scheduled/speedway/playlist/23100'; }")

        # Wait for open panels
        print("[*] Waiting for Bristol open race panels...")
        await game_frame.wait_for_selector(".market.open", timeout=20000)
        panels = await game_frame.query_selector_all(".market.open")
        print(f"[+] SUCCESS! Found {len(panels)} open race panels on Bristol!")

        # Check first race
        first_panel = panels[0]
        title_el = await first_panel.query_selector(".event-description")
        timer_el = await first_panel.query_selector("app-countdown span")
        print(f"[+] Race 1: {await title_el.inner_text()} (Countdown: {await timer_el.inner_text()})")

        await page.screenshot(path="bristol_authenticated_live.png", full_page=True)
        print("[+] Screenshot saved to: bristol_authenticated_live.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_hash_routing())
