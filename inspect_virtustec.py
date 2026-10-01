import asyncio
import json
import os
from playwright.async_api import async_playwright

URL = "https://virtual-games.virtustec.com/desktop-v4/default/?checkScroll=true&containerId=golden-race-desktop-app&profile=sportybet-dark&hwId=49690d2f-0517-46ff-bd66-6aedd9958826&showHeader=true&version=v4#/scheduled/speedway/playlist/23100"

async def inspect():
    print("[*] Launching browser to inspect VirtusTec Speedway...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )

        page = await context.new_page()

        # Block media and video streams
        async def block_media(route):
            url = route.request.url.lower()
            if any(ext in url for ext in [".mp4", ".webm", ".m3u8", ".ts", ".mp3", "video"]):
                # print(f"[-] Blocked media: {url[:60]}...")
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", block_media)

        # Track network requests
        api_requests = []
        ws_endpoints = []

        def on_request(request):
            url = request.url
            if any(k in url.lower() for k in ["api", "json", "v1", "v2", "v3", "v4", "feed", "event", "odds", "race"]):
                if not any(ext in url.lower() for ext in [".js", ".css", ".png", ".jpg", ".svg", ".woff"]):
                    api_requests.append({"method": request.method, "url": url})
                    print(f"[API Request] {request.method} {url}")

        page.on("request", on_request)

        def on_websocket(ws):
            print(f"[WebSocket Opened] {ws.url}")
            ws_endpoints.append(ws.url)
            ws.on("framereceived", lambda payload: print(f"[WS Inbound] {str(payload)[:150]}..."))
            ws.on("framesent", lambda payload: print(f"[WS Outbound] {str(payload)[:150]}..."))

        page.on("websocket", on_websocket)

        print(f"[*] Navigating to VirtusTec Speedway...")
        try:
            response = await page.goto(URL, wait_until="networkidle", timeout=45000)
            print(f"[*] HTTP Status: {response.status if response else 'None'}")
        except Exception as e:
            print(f"[!] Navigation notice/timeout: {e}")

        # Wait a bit for dynamic Vue/React/Angular app to mount
        print("[*] Waiting 10s for dynamic odds and UI to hydrate...")
        await asyncio.sleep(10)

        # Take screenshot
        screenshot_path = os.path.abspath("virtustec_speedway.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"[+] Screenshot saved to {screenshot_path}")

        # Check DOM elements
        title = await page.title()
        print(f"[+] Page Title: {title}")

        frames = page.frames
        print(f"[+] Number of frames detected: {len(frames)}")
        for i, frame in enumerate(frames):
            print(f"    Frame {i}: name='{frame.name}', url='{frame.url}'")

        # Check for canvas elements
        canvases = await page.query_selector_all("canvas")
        print(f"[+] Canvas elements detected: {len(canvases)}")

        # Check for odds or race containers
        buttons = await page.query_selector_all("button, .odd, .odds, [class*='odd'], [class*='runner'], [class*='place']")
        print(f"[+] Potential odds/runner DOM elements found: {len(buttons)}")

        # Extract text snippets
        body_text = await page.inner_text("body")
        print("\n--- Page Body Text Preview (First 800 chars) ---")
        print(body_text[:800])
        print("--- End Preview ---\n")

        with open("page_text.txt", "w", encoding="utf-8") as f:
            f.write(body_text)
        print("[+] Full body text saved to page_text.txt")

        with open("network_apis.json", "w", encoding="utf-8") as f:
            json.dump({"apis": api_requests, "websockets": ws_endpoints}, f, indent=2)
        print("[+] Network dump saved to network_apis.json")

        await browser.close()
        print("[*] Inspection complete.")

if __name__ == "__main__":
    asyncio.run(inspect())
