import asyncio
import os
import re
import sys
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, BrowserContext, Page, Frame
import config

class BrowserManager:
    def __init__(self, user_data_dir: str = config.USER_DATA_DIR, auth_path: str = config.AUTH_FILE, headless: bool = config.HEADLESS):
        self.user_data_dir = user_data_dir
        self.auth_path = auth_path
        self.headless = headless
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.game_frame: Optional[Frame] = None

    async def start(self) -> Page:
        print("[BROWSER] Launching persistent browser engine...")
        self.playwright = await async_playwright().start()

        os.makedirs(self.user_data_dir, exist_ok=True)

        launch_kwargs = {
            "user_data_dir": self.user_data_dir,
            "headless": self.headless,
            "args": config.BROWSER_ARGS,
            "viewport": {"width": 1440, "height": 900},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        }
        # Use Chrome channel on Windows if available; use standard Playwright Chromium on Linux VPS
        if sys.platform == "win32":
            launch_kwargs["channel"] = "chrome"

        self.context = await self.playwright.chromium.launch_persistent_context(**launch_kwargs)

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

        # Block media chunks (video streams, audio files)
        if config.BLOCK_MEDIA:
            async def block_media(route):
                u = route.request.url.lower()
                if any(ext in u for ext in [".mp4", ".webm", ".m3u8", ".ts", ".mp3", "video"]):
                    await route.abort()
                else:
                    await route.continue_()
            await self.page.route("**/*", block_media)

        return self.page

    async def _handle_autonomous_login(self):
        """Attempts automated login if credentials are provided in .env and not logged in."""
        if not (config.SPORTYBET_PHONE and config.SPORTYBET_PASSWORD):
            return

        try:
            # Check if user is already logged in via persistent chrome_profile
            try:
                bal_el = await self.page.wait_for_selector(".m-balance:not(:has-text('---'))", timeout=4000)
                if bal_el:
                    bal_text = (await bal_el.inner_text()).strip()
                    print(f"[BROWSER] Session already active ({bal_text}). Skipping login.")
                    return
            except Exception:
                pass

            phone_input = await self.page.query_selector("input[placeholder*='Mobile'], input[name*='phone'], input[type='tel']")
            pwd_input = await self.page.query_selector("input[type='password']")
            login_btn = await self.page.query_selector("button:has-text('Login'), input[value='Login'], .btn-login")

            if phone_input and pwd_input and login_btn and (await phone_input.is_visible()):
                print("[BROWSER] Credentials detected in .env. Performing autonomous SportyBet login...")
                await phone_input.fill(config.SPORTYBET_PHONE)
                await pwd_input.fill(config.SPORTYBET_PASSWORD)

                # Check keep me signed in
                keep_signed = await self.page.query_selector("input[type='checkbox']")
                if keep_signed:
                    is_checked = await keep_signed.is_checked()
                    if not is_checked:
                        await keep_signed.check()

                await login_btn.click()
                print("[BROWSER] Login submitted. Waiting for session authorization...")
                await asyncio.sleep(5)
        except Exception as e:
            print(f"[BROWSER] Autonomous login attempt notice: {e}")

    async def navigate_to_bristol(self) -> Frame:
        print(f"[BROWSER] Navigating to {config.SPORTYBET_URL}...")
        await self.page.goto(config.SPORTYBET_URL, wait_until="domcontentloaded", timeout=60000)

        # 1. Attempt autonomous login if logged out
        await self._handle_autonomous_login()

        # 2. Wait for SportyBet session and balance
        print("[BROWSER] Checking SportyBet session and balance...")
        try:
            bal_el = await self.page.wait_for_selector(".m-balance:not(:has-text('---'))", timeout=20000)
            bal_text = (await bal_el.inner_text()).strip()
            print(f"[BROWSER] Session Confirmed Active: {bal_text}")
        except Exception:
            print("[BROWSER] Session initializing, checking for game frame...")

        # 3. Wait for VirtusTec game frame
        print("[BROWSER] Waiting for VirtusTec game frame to attach...")
        game_frame = None
        for s in range(35):
            for f in self.page.frames:
                if "virtustec" in f.url.lower() or "golden-race" in f.url.lower():
                    game_frame = f
                    break
            if game_frame:
                break
            await asyncio.sleep(1)

        if not game_frame:
            raise RuntimeError("VirtusTec game frame failed to mount within 35s.")

        self.game_frame = game_frame
        print(f"[BROWSER] VirtusTec Game Frame mounted: {game_frame.url[:85]}...")

        # 4. Route directly to Bristol Speedway
        print("[BROWSER] Routing frame to Bristol Speedway...")
        await game_frame.evaluate(f"() => {{ window.location.hash = '{config.BRISTOL_ROUTE}'; }}")
        await asyncio.sleep(3)

        # 5. Wait for open market panels to be visible
        await game_frame.wait_for_selector(".market.open", timeout=30000)
        print("[BROWSER] Bristol Speedway market panels loaded and verified!")
        return self.game_frame

    async def get_account_balance(self) -> float:
        """Reads current real balance from SportyBet header or VirtusTec credit."""
        try:
            bal_el = await self.page.query_selector(".m-balance:not(:has-text('---'))")
            if bal_el:
                txt = (await bal_el.inner_text()).strip()
                m = re.search(r"[\d,]+(?:\.\d+)?", txt)
                if m:
                    return float(m.group(0).replace(",", ""))

            if self.game_frame:
                credit_el = await self.game_frame.query_selector(".wallet, [class*='credit']")
                if credit_el:
                    txt = (await credit_el.inner_text()).strip()
                    m = re.search(r"[\d,]+(?:\.\d+)?", txt)
                    if m:
                        return float(m.group(0).replace(",", ""))
        except Exception as e:
            print(f"[BROWSER] Balance read notice: {e}")

        return 0.0

    async def get_upcoming_race(self) -> Optional[Dict[str, Any]]:
        """Extracts the immediate next open Bristol race, countdown, and runners."""
        if not self.game_frame:
            return None

        panels = await self.game_frame.query_selector_all(".market.open")
        if not panels:
            return None

        p0 = panels[0]
        id_el = await p0.query_selector(".event-block-id")
        timer_el = await p0.query_selector("app-countdown span")
        desc_el = await p0.query_selector(".event-description")

        race_id_str = (await id_el.inner_text()).strip() if id_el else "Unknown"
        clean_race_id = re.sub(r"[^\d]", "", race_id_str)
        timer_text = (await timer_el.inner_text()).strip() if timer_el else "00:00"
        desc_text = (await desc_el.inner_text()).strip() if desc_el else "Speedway Bristol"

        seconds_left = 0
        try:
            parts = timer_text.split(":")
            if len(parts) == 2:
                seconds_left = int(parts[0]) * 60 + int(parts[1])
        except:
            seconds_left = 0

        rows = await p0.query_selector_all(".market-table-row")
        runners = []

        for r_idx, row in enumerate(rows):
            name_el = await row.query_selector(".participant-text-name")
            name = (await name_el.inner_text()).strip() if name_el else f"Runner {r_idx+1}"

            odds = await row.query_selector_all("app-odd")
            if len(odds) >= 2:
                win_txt = (await odds[0].inner_text()).strip()
                place_txt = (await odds[1].inner_text()).strip()

                try:
                    win_float = float(win_txt)
                except:
                    win_float = 0.0

                try:
                    place_float = float(place_txt)
                except:
                    place_float = 0.0

                runners.append({
                    "runner_num": r_idx + 1,
                    "runner_name": name,
                    "win_odd": win_float,
                    "place_odd": place_float,
                    "place_element": odds[1]
                })

        return {
            "race_id": clean_race_id,
            "display_id": race_id_str,
            "title": desc_text,
            "timer_text": timer_text,
            "seconds_left": seconds_left,
            "runners": runners,
            "panel": p0
        }

    async def execute_place_bet(self, runner_element, stake_amount: float) -> bool:
        """Clicks the Place odd, enters the stake in betslip, and clicks Place Bet."""
        if not self.game_frame:
            return False

        try:
            clear_btn = await self.game_frame.query_selector("a.clear")
            if clear_btn:
                await clear_btn.click()
                await asyncio.sleep(0.5)

            await runner_element.click()
            await asyncio.sleep(1.0)

            stake_str = str(int(stake_amount)) if stake_amount.is_integer() else f"{stake_amount:.2f}"
            print(f"[BROWSER] Setting stake amount {stake_str} in betslip...")

            await self.game_frame.evaluate(f"""(stake) => {{
                const input = document.getElementById('bets-stake-amount-1');
                if (input) {{
                    input.removeAttribute('readonly');
                    input.value = stake;
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                }}
            }}""", stake_str)
            await asyncio.sleep(0.5)

            bet_btn = await self.game_frame.wait_for_selector(
                "button.bet-now:not([disabled])",
                timeout=5000
            )

            btn_text = (await bet_btn.inner_text()).strip()
            print(f"[BROWSER] Clicking Betslip button: '{btn_text}'...")
            await bet_btn.click()
            await asyncio.sleep(2.0)
            print("[BROWSER] Bet placed successfully!")
            return True

        except Exception as e:
            print(f"[!] Error executing bet: {e}")
            return False

    def is_healthy(self) -> bool:
        """Returns True if browser context and page are active and responsive."""
        try:
            return bool(self.context and self.page and not self.page.is_closed() and self.game_frame)
        except Exception:
            return False

    async def restart_and_recover(self) -> Frame:
        """Restarts Chromium and recovers the session in case of unexpected browser crash or network reset."""
        print("[BROWSER] Performing automatic browser recovery and session restore...")
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass

        await self.start()
        return await self.navigate_to_bristol()

    async def close(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
