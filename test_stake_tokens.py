import asyncio
from playwright.async_api import async_playwright

URL = "https://virtual-games.virtustec.com/desktop-v4/default/?checkScroll=true&containerId=golden-race-desktop-app&profile=sportybet-dark&hwId=49690d2f-0517-46ff-bd66-6aedd9958826&showHeader=true&version=v4#/scheduled/speedway/playlist/23100"

async def test_tokens():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        await page.route("**/*", lambda route: route.abort() if any(x in route.request.url.lower() for x in [".mp4", ".webm", ".m3u8", ".ts"]) else route.continue_())
        await page.goto(URL, wait_until="load", timeout=60000)
        await page.wait_for_selector(".market.open", timeout=30000)

        # Click place odd
        odd_el = await page.wait_for_selector(".market.open .market-table-row app-odd:nth-child(4)")
        await odd_el.click()
        await asyncio.sleep(2)

        # Test clicking chip "+100"
        chip_100 = await page.wait_for_selector(".chip-button:has-text('+100')")
        if chip_100:
            print("[*] Clicking +100 chip...")
            await chip_100.click()
            await asyncio.sleep(1)

        # Test clicking chip "+250"
        chip_250 = await page.wait_for_selector(".chip-button:has-text('+250')")
        if chip_250:
            print("[*] Clicking +250 chip...")
            await chip_250.click()
            await asyncio.sleep(1)

        # Read summary text
        summary = await page.inner_text(".summary-container, .selections-container, app-betslip")
        print("Betslip text after chips:")
        for line in summary.split("\n"):
            if any(k in line.lower() for k in ["total", "stake", "winning", "place", "single"]):
                print(f"  {line.strip()}")

        await page.screenshot(path="betslip_chips_clicked.png")
        print("[+] Saved betslip_chips_clicked.png")

        # Now test how custom values work (e.g. what happens if stake is 134 or any arbitrary value)
        # Let's inspect Angular component or keypad
        has_keypad = await page.evaluate("""() => {
            const input = document.getElementById('bets-stake-amount-1');
            // Check if there is an Angular ng-reflect or control
            return {
                readonly: input ? input.readOnly : null,
                tagName: input ? input.tagName : null,
                events: input ? Object.keys(input) : []
            };
        }""")
        print("Input JS properties:", has_keypad)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_tokens())
