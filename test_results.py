import asyncio
from playwright.async_api import async_playwright

URL = "https://virtual-games.virtustec.com/desktop-v4/default/?checkScroll=true&containerId=golden-race-desktop-app&profile=sportybet-dark&hwId=49690d2f-0517-46ff-bd66-6aedd9958826&showHeader=true&version=v4#/scheduled/speedway/playlist/23100"

async def test_results():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        await page.route("**/*", lambda route: route.abort() if any(x in route.request.url.lower() for x in [".mp4", ".webm", ".m3u8", ".ts"]) else route.continue_())
        await page.goto(URL, wait_until="load", timeout=60000)
        await page.wait_for_selector(".market.open", timeout=30000)

        # Click on "Results History" in the left sidebar
        results_link = await page.wait_for_selector("a:has-text('Results History'), .nav-item:has-text('Results')")
        if results_link:
            print("[*] Clicking 'Results History'...")
            await results_link.click()
            await asyncio.sleep(3)
            await page.screenshot(path="results_history.png", full_page=True)
            print("[+] Saved results_history.png")

            # Check text
            body_text = await page.inner_text("body")
            print("Results text preview:")
            for line in body_text.split("\n")[:30]:
                if line.strip():
                    print(" ", line.strip())

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_results())
