import asyncio
import os
from playwright.async_api import async_playwright

USER_DATA = os.path.abspath("chrome_user_data")
AUTH_FILE = os.path.abspath("auth.json")

async def run_login_session():
    print("=" * 60)
    print("[*] Starting SportyBet Login Session...")
    print(f"[*] Profile Directory: {USER_DATA}")
    print("=" * 60)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            USER_DATA,
            channel="chrome",
            headless=False,
            args=[
                "--start-maximized",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # Monitor URLs to catch Speedway iframe or bet slip endpoints
        def on_req(req):
            u = req.url
            if any(k in u.lower() for k in ["speedway", "23100", "virtustec"]):
                if not any(ext in u.lower() for ext in [".svg", ".png", ".woff", ".css"]):
                    print(f"\n[INTERCEPTED SPEEDWAY CALL]: {u[:100]}...")
                    with open("speedway_endpoints.txt", "a", encoding="utf-8") as f:
                        f.write(u + "\n")

        page.on("request", on_req)

        print("[*] Navigating to SportyBet Nigeria...")
        await page.goto("https://www.sportybet.com/ng/", wait_until="domcontentloaded", timeout=60000)

        print("\n" + "=" * 60)
        print("BROWSER IS READY:")
        print("1. Log in to your SportyBet account.")
        print("2. Navigate to Virtuals -> Speedway (Bristol).")
        print("3. As soon as you log in, this script will detect your session,")
        print("   save auth.json, and keep your persistent profile.")
        print("=" * 60 + "\n")

        # Keep open for up to 15 minutes (900 seconds)
        for second in range(1, 901):
            await asyncio.sleep(1)

            if second % 5 == 0:
                cookies = await context.cookies()
                # Check for login tokens
                logged_in = any(c.get("name") in ["token", "s_id", "accessToken", "userId", "phone", "psid"] for c in cookies)

                # Save storage state periodically
                await context.storage_state(path=AUTH_FILE)

                if logged_in and second % 15 == 0:
                    print(f"[+] Active login detected! ({second}s) Storage state updated.")

            if second % 30 == 0:
                print(f"[*] Session active: {second}s elapsed. (Waiting for you to log in & reach Speedway)")

        await context.storage_state(path=AUTH_FILE)
        await context.close()
        print("[*] Session finished.")

if __name__ == "__main__":
    asyncio.run(run_login_session())
