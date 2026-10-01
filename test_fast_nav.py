import asyncio
import os
from playwright.async_api import async_playwright
import config

async def test_fast_nav():
    print("[*] Testing ultra-fast navigation with wait_until='commit'...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=config.BROWSER_ARGS)
        context = await browser.new_context(storage_state=config.AUTH_FILE, viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Block heavy media
        async def block_media(route):
            u = route.request.url.lower()
            if any(u.endswith(ext) or (ext + "?") in u for ext in [".mp4", ".webm", ".m3u8", ".ts", ".mp3", ".aac"]):
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", block_media)

        t0 = asyncio.get_event_loop().time()
        # Navigate with commit
        await page.goto(config.SPORTYBET_URL, wait_until="commit", timeout=45000)
        print(f"[+] Navigated (committed) in {asyncio.get_event_loop().time() - t0:.2f}s!")

        print("[*] Waiting for VirtusTec game frame...")
        game_frame = None
        for s in range(40):
            for f in page.frames:
                if "virtustec" in f.url.lower() or "golden-race" in f.url.lower():
                    game_frame = f
                    break
            if game_frame:
                print(f"[+] Found VirtusTec frame after {s}s! URL:\n  {game_frame.url}")
                break
            await asyncio.sleep(1)

        if game_frame:
            # Route to Bristol
            print("[*] Routing frame to Bristol...")
            await game_frame.evaluate(f"() => {{ window.location.hash = '{config.BRISTOL_ROUTE}'; }}")
            await asyncio.sleep(3)
            panels = await game_frame.query_selector_all(".market.open")
            print(f"[+] Open race panels on Bristol: {len(panels)}")

        await page.screenshot(path="fast_nav_success.png", full_page=True)
        print("[+] Screenshot saved: fast_nav_success.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_fast_nav())
