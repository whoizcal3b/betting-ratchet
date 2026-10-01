import asyncio
from playwright.async_api import async_playwright

URL = "https://virtual-games.virtustec.com/desktop-v4/default/?checkScroll=true&containerId=golden-race-desktop-app&profile=sportybet-dark&hwId=49690d2f-0517-46ff-bd66-6aedd9958826&showHeader=true&version=v4#/scheduled/speedway/playlist/23100"

async def inspect_stake_input():
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

        # Find stake input
        input_el = await page.query_selector("app-betslip input")
        if input_el:
            html = await input_el.evaluate("el => el.outerHTML")
            print("Stake Input Element:")
            print(html)
            # Test filling
            await input_el.fill("250")
            await asyncio.sleep(1)
            val = await input_el.input_value()
            print(f"Filled stake input with: {val}")

            # Re-check total stake
            total_stake_el = await page.query_selector(".total-stake, [class*='total-stake'], .summary")
            if total_stake_el:
                print("Total stake summary:", await total_stake_el.inner_text())

            await page.screenshot(path="betslip_filled.png")
            print("[+] Saved betslip_filled.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_stake_input())
