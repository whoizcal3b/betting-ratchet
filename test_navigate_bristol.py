import asyncio
import os
from playwright.async_api import async_playwright

AUTH_PATH = os.path.abspath("auth.json")

async def navigate_bristol():
    print("[*] Launching browser to navigate to Bristol...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--mute-audio",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = await browser.new_context(
            storage_state=AUTH_PATH,
            viewport={"width": 1440, "height": 900}
        )
        page = await context.new_page()

        # Block media
        await page.route("**/*", lambda route: route.abort() if any(x in route.request.url.lower() for x in [".mp4", ".webm", ".m3u8", ".ts", ".mp3", "video"]) else route.continue_())

        print("[*] Navigating to https://www.sportybet.com/ng/virtual/...")
        await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="domcontentloaded", timeout=60000)

        # Wait for iframe to appear in DOM
        print("[*] Waiting for game iframe to attach...")
        iframe_handle = await page.wait_for_selector("iframe", timeout=35000)
        src = await iframe_handle.get_attribute("src")
        print(f"[+] Found iframe element with src:\n  {src}\n")

        game_frame = await iframe_handle.content_frame()
        if not game_frame:
            print("[!] Unable to get content_frame from iframe handle.")
            await browser.close()
            return

        print(f"[+] Successfully attached to Game Frame: {game_frame.url}")

        # Wait for frame DOM to load
        await game_frame.wait_for_selector(".nav-item, a, button, .menu", timeout=30000)
        print("[+] Game Frame UI mounted!")

        # Check balance in frame
        credit_el = await game_frame.query_selector("text=CREDIT, [class*='credit'], .wallet")
        if credit_el:
            print(f"[+] Frame Credit Text: {await credit_el.inner_text()}")

        # Click Speedway in frame menu
        print("[*] Clicking Speedway in frame menu...")
        speedway_el = await game_frame.wait_for_selector("a:has-text('Speedway'), [title*='Speedway'], span:has-text('Speedway')", timeout=15000)
        if speedway_el:
            await speedway_el.click()
            print("[+] Speedway clicked. Waiting for Bristol submenu...")
            await asyncio.sleep(2)

            bristol_el = await game_frame.wait_for_selector("a:has-text('Bristol'), [title*='Bristol'], span:has-text('Bristol')", timeout=10000)
            if bristol_el:
                await bristol_el.click()
                print("[+] Bristol clicked! Waiting for race panels...")
                await asyncio.sleep(4)

        # Count open race panels
        panels = await game_frame.query_selector_all(".market.open")
        print(f"[+] Verified {len(panels)} open Bristol race panels!")

        # Screenshot
        await page.screenshot(path="authenticated_bristol_confirmed.png", full_page=True)
        print("[+] Screenshot saved to: authenticated_bristol_confirmed.png")

        await browser.close()
        print("[*] Done!")

if __name__ == "__main__":
    asyncio.run(navigate_bristol())
