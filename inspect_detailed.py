import asyncio
import json
import os
from playwright.async_api import async_playwright

URL = "https://virtual-games.virtustec.com/desktop-v4/default/?checkScroll=true&containerId=golden-race-desktop-app&profile=sportybet-dark&hwId=49690d2f-0517-46ff-bd66-6aedd9958826&showHeader=true&version=v4#/scheduled/speedway/playlist/23100"

async def inspect_detailed():
    print("[*] Launching browser with full console & network logging...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[PAGE ERROR] {err}"))

        ws_messages = []
        def on_websocket(ws):
            print(f"[WebSocket Opened] {ws.url}")
            def on_recv(payload):
                try:
                    data = json.loads(payload)
                    ws_messages.append({"dir": "IN", "data": data})
                    # print snippet
                    typ = data.get("type", "")
                    print(f"<- WS IN: type={typ} keys={list(data.keys())}")
                except:
                    ws_messages.append({"dir": "IN", "raw": str(payload)[:200]})
            def on_sent(payload):
                try:
                    data = json.loads(payload)
                    ws_messages.append({"dir": "OUT", "data": data})
                    print(f"-> WS OUT: type={data.get('type')} keys={list(data.keys())}")
                except:
                    ws_messages.append({"dir": "OUT", "raw": str(payload)[:200]})

            ws.on("framereceived", on_recv)
            ws.on("framesent", on_sent)

        page.on("websocket", on_websocket)

        # Do NOT block any media this time, let's see if video player or scripts were blocked
        print(f"[*] Navigating...")
        await page.goto(URL, wait_until="load", timeout=60000)

        print("[*] Waiting 15s to observe UI lifecycle...")
        await asyncio.sleep(15)

        # Screenshot
        await page.screenshot(path="virtustec_unblocked.png", full_page=True)
        print("[+] Screenshot saved to virtustec_unblocked.png")

        # Save logs
        with open("console_logs.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(console_logs))

        with open("ws_messages.json", "w", encoding="utf-8") as f:
            json.dump(ws_messages, f, indent=2)

        print(f"[+] Recorded {len(console_logs)} console lines and {len(ws_messages)} WS messages.")

        # Let's inspect the HTML of the main container
        container = await page.content()
        with open("page_dom.html", "w", encoding="utf-8") as f:
            f.write(container)
        print("[+] Saved page_dom.html")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_detailed())
