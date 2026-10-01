import asyncio
import os
import re
from playwright.async_api import async_playwright

AUTH_PATH = os.path.abspath("auth.json")

async def test_frame():
    print("[*] Launching browser to navigate properly to Bristol...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=["--mute-audio"])
        context = await browser.new_context(storage_state=AUTH_PATH, viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        await page.route("**/*", lambda route: route.abort() if any(x in route.request.url.lower() for x in [".mp4", ".webm", ".m3u8", ".ts", ".mp3", "video"]) else route.continue_())
        await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="domcontentloaded", timeout=60000)

        # Wait for the specific virtustec iframe to appear
        print("[*] Waiting for virtustec iframe...")
        iframe_handle = await page.wait_for_selector("iframe[src*='virtustec']", timeout=40000)
        game_frame = await iframe_handle.content_frame()
        print(f"[+] Attached to VirtusTec frame: {game_frame.url}")

        # Wait for frame DOM
        await game_frame.wait_for_selector(".nav-item, a, .menu", timeout=25000)
        print("[+] Game UI loaded!")

        # Navigate directly to Speedway Bristol hash
        print("[*] Switching route to Speedway Bristol...")
        await game_frame.evaluate("() => { window.location.hash = '#/scheduled/speedway/playlist/23100'; }")
        await asyncio.sleep(4)

        # Check race panels
        panels = await game_frame.query_selector_all(".market.open")
        print(f"[+] Found {len(panels)} open race panels on Bristol!")

        # Print all 4 runners and odds for the first race
        if panels:
            first_panel = panels[0]
            header = await first_panel.query_selector(".event-description")
            timer = await first_panel.query_selector("app-countdown span")
            print(f"\n[NEXT RACE]: {await header.inner_text()} (Countdown: {await timer.inner_text()})")

            rows = await first_panel.query_selector_all(".market-table-row")
            for r_idx, row in enumerate(rows):
                name_el = await row.query_selector(".participant-text-name")
                odds = await row.query_selector_all("app-odd")
                if len(odds) >= 2:
                    win = (await odds[0].inner_text()).strip()
                    place = (await odds[1].inner_text()).strip()
                    print(f"  Runner {r_idx+1}: {await name_el.inner_text():<20} | WIN: {win:<5} | PLACE: {place:<5}")

            # Check betslip button
            bet_btn = await game_frame.query_selector(".bet-now")
            if bet_btn:
                print(f"\n[+] Betslip Button text: '{await bet_btn.inner_text()}'")

        await page.screenshot(path="bristol_live_confirmed.png", full_page=True)
        print("[+] Saved screenshot: bristol_live_confirmed.png")

        await browser.close()
        print("[*] Success!")

if __name__ == "__main__":
    asyncio.run(test_frame())
