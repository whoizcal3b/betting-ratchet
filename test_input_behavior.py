import asyncio
from playwright.async_api import async_playwright

URL = "https://virtual-games.virtustec.com/desktop-v4/default/?checkScroll=true&containerId=golden-race-desktop-app&profile=sportybet-dark&hwId=49690d2f-0517-46ff-bd66-6aedd9958826&showHeader=true&version=v4#/scheduled/speedway/playlist/23100"

async def test_input_behavior():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Block media
        await page.route("**/*", lambda route: route.abort() if any(x in route.request.url.lower() for x in [".mp4", ".webm", ".m3u8", ".ts"]) else route.continue_())

        await page.goto(URL, wait_until="load", timeout=60000)
        await page.wait_for_selector(".market.open", timeout=30000)

        # Click first place odd
        first_place_odd = await page.wait_for_selector(".market.open .market-table-row app-odd:nth-child(4)")
        if first_place_odd:
            await first_place_odd.click()
            await asyncio.sleep(2)

        # 1. Check clicking the input box
        input_el = await page.query_selector("#bets-stake-amount-1")
        if input_el:
            print("[*] Clicking stake input element...")
            await input_el.click()
            await asyncio.sleep(1)
            await page.screenshot(path="betslip_after_input_click.png")

            # Check if a keypad or modal popped up
            keypad = await page.query_selector(".keypad, app-keypad, [class*='keypad'], [class*='numpad']")
            if keypad:
                print(f"[+] Keypad found: {await keypad.evaluate('el => el.className')}")

            # 2. Check token / chip buttons (+100, +250, etc.)
            chips = await page.query_selector_all("app-betslip .token, app-betslip [class*='token'], app-betslip [class*='chip'], app-betslip button")
            print(f"[+] Found {len(chips)} possible chip/token buttons.")
            for c in chips:
                txt = (await c.inner_text()).strip()
                if txt:
                    print(f"    Button: '{txt}' class='{await c.evaluate('el => el.className')}'")

            # 3. Test programmatic value injection via JS
            print("[*] Testing programmatic value injection via evaluate...")
            await page.evaluate("""() => {
                const el = document.getElementById('bets-stake-amount-1');
                if (el) {
                    el.removeAttribute('readonly');
                    el.value = '350';
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""")
            await asyncio.sleep(1)

            # Check what total stake displays
            total_txt = await page.evaluate("""() => {
                const total = document.querySelector('.total-stake') || document.querySelector('.summary') || document.querySelector('.bet-button-container');
                return total ? total.innerText : 'None';
            }""")
            print(f"[+] Total/Summary after JS injection: {total_txt}")

            await page.screenshot(path="betslip_after_js_inject.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_input_behavior())
