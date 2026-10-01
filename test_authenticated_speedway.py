import asyncio
import os
from playwright.async_api import async_playwright

AUTH_PATH = os.path.abspath("auth.json")

async def test_auth():
    print("[*] Launching browser with saved auth.json...")
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

        # Block all video, media, and audio streams
        async def block_media(route):
            url = route.request.url.lower()
            if any(ext in url for ext in [".mp4", ".webm", ".m3u8", ".ts", ".mp3", "video"]):
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", block_media)

        print("[*] Navigating to https://www.sportybet.com/ng/virtual/...")
        await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        # Check SportyBet balance on the parent page
        balance_el = await page.query_selector(".m-balance, [class*='balance'], .m-user-info")
        if balance_el:
            bal_text = await balance_el.inner_text()
            print(f"[+] SportyBet Header User Info/Balance: {bal_text.strip()}")
        else:
            print("[-] No header balance element found on sportybet parent page.")

        # Inspect iframes
        frames = page.frames
        print(f"[+] Total frames found: {len(frames)}")

        game_frame = None
        for idx, f in enumerate(frames):
            print(f"  Frame {idx}: {f.url[:100]}...")
            if any(k in f.url.lower() for k in ["virtustec", "golden-race", "speedway"]):
                game_frame = f

        if game_frame:
            print(f"\n[+] Found Authenticated VirtusTec Game Frame:\n  {game_frame.url}\n")

            # Wait for open market panels in the frame
            try:
                await game_frame.wait_for_selector(".market.open", timeout=25000)
                print("[+] Open market panels loaded inside authenticated frame!")

                # Check betslip button status
                bet_btn = await game_frame.query_selector(".bet-now, button:has-text('Place bet'), button:has-text('Login')")
                if bet_btn:
                    btn_text = (await bet_btn.inner_text()).strip()
                    btn_disabled = await bet_btn.get_attribute("disabled")
                    print(f"[+] Betslip Button text: '{btn_text}' | Disabled: {btn_disabled is not None}")

                # Check wallet / balance inside VirtusTec frame
                wallet_el = await game_frame.query_selector(".wallet, [class*='wallet'], .balance, [class*='balance']")
                if wallet_el:
                    print(f"[+] VirtusTec Frame Wallet/Balance: {await wallet_el.inner_text()}")

            except Exception as e:
                print(f"[!] Notice inside game frame: {e}")

        # Take full screenshot
        screenshot_path = os.path.abspath("authenticated_speedway_verified.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"[+] Screenshot saved to: {screenshot_path}")

        await browser.close()
        print("[*] Authentication test complete.")

if __name__ == "__main__":
    asyncio.run(test_auth())
