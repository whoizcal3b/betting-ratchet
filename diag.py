import asyncio
import os
from playwright.async_api import async_playwright
import config

async def diag():
    print("[*] Diagnosing /ng/virtual/ frame mounting...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=config.BROWSER_ARGS)
        context = await browser.new_context(storage_state=config.AUTH_FILE, viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Track network calls
        page.on("request", lambda r: print(f"REQ: {r.method} {r.url[:90]}") if any(k in r.url.lower() for k in ["virtus", "golden", "token", "hash", "virtual"]) else None)

        await page.goto(config.SPORTYBET_URL, wait_until="domcontentloaded", timeout=60000)
        print("[*] Loaded domcontentloaded, waiting 15s...")
        for s in range(15):
            await asyncio.sleep(1)
            frames = [f.url for f in page.frames]
            if len(frames) > 1:
                print(f"[+] Frame appeared at {s}s! Frames: {frames}")
                break

        await page.screenshot(path="diag_screenshot.png", full_page=True)
        print(f"[+] Final frames: {[f.url for f in page.frames]}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(diag())
