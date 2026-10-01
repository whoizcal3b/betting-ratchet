import asyncio
import os
from playwright.async_api import async_playwright

AUTH_PATH = os.path.abspath("auth.json")

async def test():
    print("[*] Launching browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=["--mute-audio"])
        context = await browser.new_context(storage_state=AUTH_PATH, viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Block media
        await page.route("**/*", lambda route: route.abort() if any(x in route.request.url.lower() for x in [".mp4", ".webm", ".m3u8", ".ts", ".mp3", "video"]) else route.continue_())

        print("[*] Navigating to https://www.sportybet.com/ng/virtual/...")
        await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="domcontentloaded", timeout=60000)

        # Wait for virtustec frame via frame list polling
        print("[*] Waiting for VirtusTec frame...")
        game_frame = None
        for _ in range(40):
            for f in page.frames:
                if "virtustec" in f.url.lower():
                    game_frame = f
                    break
            if game_frame:
                break
            await asyncio.sleep(1)

        if not game_frame:
            print("[!] VirtusTec frame not found after 40s.")
            await browser.close()
            return

        print(f"[+] Found VirtusTec Frame! URL:\n  {game_frame.url}")

        # Wait for frame DOM
        await game_frame.wait_for_selector(".nav-item, a, .menu", timeout=30000)
        print("[+] Game UI loaded!")

        # Click Speedway
        speedway_el = await game_frame.wait_for_selector("a:has-text('Speedway'), [title*='Speedway']", timeout=15000)
        await speedway_el.click()
        print("[+] Clicked Speedway.")
        await asyncio.sleep(2)

        # Dispatch click on Bristol link
        print("[*] Dispatching click on Bristol link...")
        await game_frame.evaluate("""() => {
            const link = document.querySelector("a[href*='23100']") || document.querySelector("a[title='Bristol']");
            if (link) {
                link.click();
            }
        }""")
        await asyncio.sleep(4)

        # Check frame URL and open panels
        print(f"[+] Current frame URL: {game_frame.url}")
        panels = await game_frame.query_selector_all(".market.open")
        print(f"[+] Open race panels: {len(panels)}")

        if panels:
            p0 = panels[0]
            header = await p0.query_selector(".event-description")
            timer = await p0.query_selector("app-countdown span")
            print(f"[+] Next Race: {await header.inner_text()} (Countdown: {await timer.inner_text()})")

            # Check bet button text
            btn = await game_frame.query_selector(".bet-now")
            if btn:
                print(f"[+] Betslip Button: '{await btn.inner_text()}' (Disabled: {await btn.get_attribute('disabled') is not None})")

        await page.screenshot(path="bristol_click_result.png", full_page=True)
        print("[+] Screenshot saved: bristol_click_result.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
