import asyncio
import json
import os
from playwright.async_api import async_playwright
import config

async def check_auth_status():
    print("[*] Inspecting SportyBet authentication status...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=config.BROWSER_ARGS)
        context = await browser.new_context(storage_state=config.AUTH_FILE, viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        api_responses = []
        def on_response(res):
            u = res.url.lower()
            if any(k in u for k in ["balance", "profile", "account", "user", "token", "refresh", "virtual"]):
                if not any(ext in u for ext in [".js", ".css", ".png", ".jpg", ".svg", ".woff"]):
                    try:
                        print(f"[API RESPONSE] {res.status} {res.request.method} {res.url[:85]}")
                        api_responses.append({"status": res.status, "url": res.url})
                    except:
                        pass
        page.on("response", on_response)

        await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(8)

        # Check balance text
        bal_el = await page.query_selector(".m-balance, [class*='balance']")
        if bal_el:
            print(f"[+] Balance element text: '{await bal_el.inner_text()}'")

        # Check cookies
        cookies = await context.cookies()
        token_cookies = [c for c in cookies if any(k in c["name"].lower() for k in ["token", "auth", "session", "user"])]
        print(f"[+] Total cookies: {len(cookies)}, Auth-related: {len(token_cookies)}")
        for c in token_cookies:
            print(f"  {c['name']} = {c['value'][:25]}... (expires: {c.get('expires')})")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_auth_status())
