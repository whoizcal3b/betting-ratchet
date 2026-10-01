import asyncio
import os
from playwright.async_api import async_playwright

AUTH_PATH = os.path.abspath("auth.json")

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=["--mute-audio"])
        context = await browser.new_context(storage_state=AUTH_PATH, viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        blocked_urls = []
        # Stricter media blocking (extensions only, NOT generic words like 'video')
        async def block_media(route):
            url = route.request.url.lower()
            if any(url.endswith(ext) or (ext + "?") in url for ext in [".mp4", ".webm", ".m3u8", ".ts", ".mp3", ".aac", ".wav"]):
                blocked_urls.append(url)
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", block_media)

        print("[*] Navigating to https://www.sportybet.com/ng/virtual/...")
        await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="load", timeout=60000)
        await asyncio.sleep(5)

        print(f"[+] Total frames: {len(page.frames)}")
        for idx, f in enumerate(page.frames):
            print(f"  Frame {idx}: {f.url}")

        await page.screenshot(path="sportybet_check.png")
        print(f"[+] Blocked {len(blocked_urls)} actual media files.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check())
