import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

AUTH_FILE = os.path.abspath("auth.json")
SPORTYBET_URL = "https://www.sportybet.com/ng/"

async def main():
    print("=" * 60)
    print("[*] Launching visible Chrome window for SportyBet Login...")
    print("=" * 60)

    async with async_playwright() as p:
        # Launch native Chrome in headful mode
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = await browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )

        page = await context.new_page()

        # Intercept and log iframe URLs or any VirtusTec / Golden Race traffic
        speedway_urls = []

        def on_request(request):
            url = request.url
            if any(k in url.lower() for k in ["virtustec", "golden-race", "speedway", "23100"]):
                if not any(ext in url.lower() for ext in [".png", ".jpg", ".svg", ".woff", ".css", ".mp4", ".ts"]):
                    print(f"\n[INTERCEPTED GAME URL]:\n{url}\n")
                    speedway_urls.append(url)
                    with open("intercepted_urls.txt", "a", encoding="utf-8") as f:
                        f.write(url + "\n\n")

        page.on("request", on_request)

        print(f"[*] Navigating to {SPORTYBET_URL}...")
        try:
            await page.goto(SPORTYBET_URL, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"[!] Notice: {e}")

        print("\n" + "=" * 60)
        print("ACTION REQUIRED:")
        print("1. Log in to your SportyBet account in the opened Chrome window.")
        print("2. Navigate to Virtuals -> Speedway (Bristol).")
        print("3. When you have logged in and reached the page, the script will")
        print("   automatically save your session to auth.json and capture the URLs.")
        print("=" * 60 + "\n")

        # Monitor loop for 10 minutes (600 seconds)
        for i in range(120):
            await asyncio.sleep(5)

            # Check if user has logged in by saving storage state periodically
            try:
                cookies = await context.cookies()
                has_auth_cookie = any(c.get("name") in ["token", "s_id", "accessToken", "userId", "phone", "psid"] for c in cookies)

                # Save storage state
                await context.storage_state(path=AUTH_FILE)

                # Check if we are on a virtuals page or have cookies
                current_url = page.url
                if i % 6 == 0:
                    print(f"[*] Status ({i*5}s): Current page: {current_url[:60]}... Cookies captured: {len(cookies)}")

                if len(speedway_urls) > 0 and has_auth_cookie:
                    print("\n[+] SUCCESS! Both login auth cookies and Speedway game URL captured!")
                    print(f"[+] auth.json written ({os.path.getsize(AUTH_FILE)} bytes).")
                    print(f"[+] Latest Game URL: {speedway_urls[-1]}")
                    break
            except Exception as ex:
                pass

        print("\n[*] Saving final storage state to auth.json...")
        await context.storage_state(path=AUTH_FILE)
        print(f"[+] Saved to {AUTH_FILE}")

        # Keep browser open an extra 10 seconds to make sure everything settled
        await asyncio.sleep(10)
        await browser.close()
        print("[*] Browser closed. Session captured successfully.")

if __name__ == "__main__":
    asyncio.run(main())
