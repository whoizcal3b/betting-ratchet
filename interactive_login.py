import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright
import config

async def main():
    print("=" * 60)
    print("   SPORTYBET PERMANENT LOGIN & PERSISTENT PROFILE SETUP")
    print("=" * 60)
    print(f"\n[+] Chrome Profile Directory: {config.USER_DATA_DIR}")

    os.makedirs(config.USER_DATA_DIR, exist_ok=True)

    async with async_playwright() as p:
        # Launch persistent browser profile
        context = await p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            channel="chrome",
            headless=False,
            args=[
                "--start-maximized",
                "--mute-audio",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print("[*] Opening SportyBet Scheduled Virtuals (/ng/virtual/)...")
        await page.goto(config.SPORTYBET_URL)

        print("\n" + "*" * 60)
        print("ACTION:")
        print("1. Log in to your SportyBet account using the fields at the top.")
        print("2. Check 'Keep me signed in' checkbox.")
        print("3. Once you click Login and your balance shows in the header,")
        print("   switch back here and press [ENTER].")
        print("*" * 60 + "\n")

        # Wait for user input in console
        await asyncio.to_thread(input, "Press ENTER after you have logged in: ")

        print("\n[*] Saving persistent session and auth state...")
        await context.storage_state(path=config.AUTH_FILE)

        # Check balance
        bal_el = await page.query_selector(".m-balance:not(:has-text('---'))")
        if bal_el:
            print(f"[+] Verified Balance: {(await bal_el.inner_text()).strip()}")

        print(f"[SUCCESS] Persistent profile saved to {config.USER_DATA_DIR}!")
        print(f"[SUCCESS] auth.json snapshot saved to {config.AUTH_FILE}!")
        print("\nYou can now close the browser. Ready to automate!")
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
