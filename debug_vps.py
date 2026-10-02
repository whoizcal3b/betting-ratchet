import asyncio
import os
import sys
import json
from playwright.async_api import async_playwright

async def run_diagnostics():
    print("=" * 60)
    print("      VIRTUAL RATCHET - LIVE VPS BROWSER & NETWORK DIAGNOSTIC")
    print("=" * 60)

    # 1. Check IP via python
    import urllib.request
    try:
        req = urllib.request.Request("http://ip-api.com/json", headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"[NET] Outbound IP: {data.get('query')} | Country: {data.get('country')} | City: {data.get('city')}")
    except Exception as e:
        print(f"[NET] IP lookup error: {e}")

    # 2. Launch persistent Chromium using same profile
    base_dir = os.path.dirname(os.path.abspath(__file__))
    profile_dir = os.path.join(base_dir, "chrome_profile")
    
    print("\n[BROWSER] Launching Chromium persistent context...")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            viewport={"width": 1440, "height": 900}
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print("[BROWSER] Loading https://www.sportybet.com/ng/virtual/...")
        try:
            await page.goto("https://www.sportybet.com/ng/virtual/", wait_until="domcontentloaded", timeout=45000)
            print("[BROWSER] DOM Content Loaded! Waiting 10s for scripts and iframes...")
            await asyncio.sleep(10)
        except Exception as e:
            print(f"[!] Navigation error: {e}")

        # Check page title and URL
        print(f"\n[PAGE] Current URL:   {page.url}")
        print(f"[PAGE] Current Title: {await page.title()}")

        # Check if balance is visible
        bal_el = await page.query_selector(".m-balance")
        if bal_el:
            print(f"[PAGE] Balance element: '{(await bal_el.inner_text()).strip()}'")

        # Check all frames in the page
        frames = page.frames
        print(f"\n[FRAMES] Total frames attached: {len(frames)}")
        for i, f in enumerate(frames):
            print(f"  Frame #{i}: name='{f.name}' | url='{f.url[:110]}'")

        # Check all iframe DOM elements
        iframes = await page.query_selector_all("iframe")
        print(f"\n[IFRAMES] Total <iframe> tags in DOM: {len(iframes)}")
        for j, ifr in enumerate(iframes):
            src = await ifr.get_attribute("src") or "NO_SRC"
            name = await ifr.get_attribute("name") or "NO_NAME"
            cls = await ifr.get_attribute("class") or "NO_CLASS"
            is_vis = await ifr.is_visible()
            print(f"  Tag #{j}: src='{src[:100]}' | visible={is_vis} | class='{cls}'")

        # Check for modals, popups, or maintenance banners
        modals = await page.query_selector_all(".m-dialog, .popup, .modal, [class*='overlay'], [class*='dialog']")
        if modals:
            print(f"\n[POPUPS] Found {len(modals)} modal/dialog elements:")
            for m in modals:
                if await m.is_visible():
                    txt = (await m.inner_text()).strip().replace('\n', ' ')
                    print(f"  Visible Modal: '{txt[:120]}'")

        # Take screenshot
        screenshot_path = os.path.join(base_dir, "vps_debug.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n[+] Full-page screenshot saved to '{screenshot_path}'")

        await context.close()

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
