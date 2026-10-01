import asyncio
import json
import os
from playwright.async_api import async_playwright
import config

async def inspect_goldenrace_login():
    print("[*] Inspecting goldenrace-account-v4/login endpoint...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=config.BROWSER_ARGS)
        context = await browser.new_context(storage_state=config.AUTH_FILE, viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        async def on_response(res):
            if "goldenrace-account-v4/login" in res.url:
                print(f"\n[FOUND GOLDENRACE LOGIN RESPONSE]: Status {res.status}")
                try:
                    body = await res.json()
                    print(json.dumps(body, indent=2))
                    with open("goldenrace_login_res.json", "w", encoding="utf-8") as f:
                        json.dump(body, f, indent=2)
                except Exception as e:
                    print("Error reading json:", e)

        page.on("response", on_response)
        await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_goldenrace_login())
