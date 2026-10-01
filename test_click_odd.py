import asyncio
import re
from playwright.async_api import async_playwright

URL = "https://virtual-games.virtustec.com/desktop-v4/default/?checkScroll=true&containerId=golden-race-desktop-app&profile=sportybet-dark&hwId=49690d2f-0517-46ff-bd66-6aedd9958826&showHeader=true&version=v4#/scheduled/speedway/playlist/23100"

async def test_click():
    print("[*] Launching browser to test odds selection and betslip interaction...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Block media to keep it fast
        async def block_media(route):
            url = route.request.url.lower()
            if any(ext in url for ext in [".mp4", ".webm", ".m3u8", ".ts", ".mp3"]):
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", block_media)

        print("[*] Navigating to Speedway...")
        await page.goto(URL, wait_until="load", timeout=60000)

        # Wait for the first race panel to appear
        print("[*] Waiting for open race panels...")
        await page.wait_for_selector(".market.open", timeout=30000)
        await asyncio.sleep(3)

        # Query all open panels
        panels = await page.query_selector_all(".market.open")
        print(f"[+] Found {len(panels)} open race panels.")

        for i, panel in enumerate(panels):
            # Extract countdown
            timer_el = await panel.query_selector("app-countdown span")
            timer_text = await timer_el.inner_text() if timer_el else "N/A"

            # Extract race title & ID
            title_el = await panel.query_selector(".event-description")
            id_el = await panel.query_selector(".event-block-id")
            title_text = await title_el.inner_text() if title_el else "Speedway"
            id_text = await id_el.inner_text() if id_el else ""

            print(f"\n--- Race {i+1}: {title_text} {id_text} (Starts in: {timer_text}) ---")

            # Extract rows
            rows = await panel.query_selector_all(".market-table-row")
            runners_info = []

            for r_idx, row in enumerate(rows):
                name_el = await row.query_selector(".participant-text-name")
                name_text = await name_el.inner_text() if name_el else f"Runner {r_idx+1}"

                # Place odd is the second app-odd in the row
                odds_els = await row.query_selector_all("app-odd")
                if len(odds_els) >= 2:
                    win_odd_el = odds_els[0]
                    place_odd_el = odds_els[1]

                    win_val = (await win_odd_el.inner_text()).strip()
                    place_val = (await place_odd_el.inner_text()).strip()

                    try:
                        p_float = float(place_val)
                    except:
                        p_float = 0.0

                    runners_info.append({
                        "runner_num": r_idx + 1,
                        "name": name_text,
                        "win_odd": win_val,
                        "place_odd": place_val,
                        "place_float": p_float,
                        "place_element": place_odd_el
                    })

                    print(f"  #{r_idx+1}: {name_text:<20} | WIN: {win_val:<5} | PLACE: {place_val:<5}")

            # Test strategy decision for this race
            qualifying = [r for r in runners_info if r["place_float"] >= 2.80]
            print(f"  -> Qualifying runners (>= 2.80): {len(qualifying)}")
            for q in qualifying:
                print(f"     Candidate #{q['runner_num']} {q['name']}: {q['place_odd']}")

            # If this is the upcoming race (Race 1), let's click one odd to test the betslip!
            if i == 0 and runners_info:
                # Pick the highest or candidate
                target = max(qualifying, key=lambda x: x["place_float"]) if qualifying else runners_info[0]
                print(f"\n[ACTION] Clicking Place odd on #{target['runner_num']} ({target['name']} @ {target['place_odd']})...")
                await target["place_element"].click()
                await asyncio.sleep(2)

                # Check betslip
                betslip_el = await page.query_selector("app-betslip")
                if betslip_el:
                    betslip_html = await betslip_el.inner_html()
                    print("\n--- Betslip Content After Click ---")
                    print(betslip_html[:1500])

                await page.screenshot(path="betslip_clicked.png", full_page=True)
                print("[+] Saved screenshot: betslip_clicked.png")
                break

        await browser.close()
        print("[*] Test finished successfully.")

if __name__ == "__main__":
    asyncio.run(test_click())
