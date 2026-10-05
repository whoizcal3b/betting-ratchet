import asyncio
import os
import sys
import datetime
import time
from typing import Optional, Dict, Any

import config
from db.journal import DatabaseJournal
from engine.math_engine import MathEngine, AccountLiquidatedException
from engine.odds_analyzer import OddsAnalyzer
from core.ws_listener import VirtusTecWsListener
from core.browser_manager import BrowserManager
from core.telegram_notifier import TelegramNotifier

class VirtualRatchetBot:
    def __init__(self):
        print("=" * 65)
        print("   VIRTUAL RATCHET: HIGH-WATER MARK AUTOMATED BETTING BOT")
        print("=" * 65)

        self.db = DatabaseJournal(config.DB_FILE)

        # Handle DB reset if requested in .env
        if config.RESET_DB_ON_START:
            print("[*] RESET_DB_ON_START=True: Resetting account state in DB...")
            self.db.update_account_state(
                current_balance=config.INITIAL_BALANCE,
                peak_balance=config.INITIAL_BALANCE,
                max_drawdown=0.0,
                wins=0,
                losses=0
            )
            self.db.update_last_milestone(0)

        self.state = self.db.load_account_state(initial_balance=config.INITIAL_BALANCE)
        self.last_reported_milestone = self.state.get("last_reported_milestone", 0)

        self.math_engine = MathEngine(
            initial_balance=self.state["current_balance"],
            divisor=config.DEFAULT_DIVISOR,
            peak_balance=self.state["peak_balance"],
            mdd_trough=self.state["max_drawdown_trough"],
            is_paper=(config.BOT_MODE == "PAPER")
        )

        self.odds_analyzer = OddsAnalyzer(min_odds=config.TARGET_ODDS_MIN)
        self.ws_listener = VirtusTecWsListener(callback=self._on_resolution)
        self.telegram = TelegramNotifier()

        # Stream reconnect coordination (only the main loop ever reloads the page)
        self.reconnect_requested = False
        self._last_reconnect_ts = 0.0
        self.current_seconds_left: Optional[int] = None
        self.browser_manager = BrowserManager(
            user_data_dir=config.USER_DATA_DIR,
            auth_path=config.AUTH_FILE,
            headless=config.HEADLESS
        )

        mode_badge = "[PAPER TRADING / SIMULATION]" if config.BOT_MODE == "PAPER" else "[LIVE REAL-MONEY BETTING]"
        db_ok = self.db.check_integrity()
        print(f"[*] Mode:                 {mode_badge}")
        print(f"[*] Starting Capital:     NGN {config.INITIAL_BALANCE:,.2f}")
        print(f"[*] Current Balance:      NGN {self.math_engine.current_balance:,.2f}")
        print(f"[*] Peak Balance:         NGN {self.math_engine.peak_balance:,.2f}")
        r_step = 100.0 / config.DEFAULT_DIVISOR
        cur_dd = self.math_engine.get_current_drawdown_pct()
        cur_dd_r = cur_dd / r_step if r_step > 0 else 0
        mdd_r = self.math_engine.mdd_trough_pct / r_step if r_step > 0 else 0
        print(f"[*] Current Drawdown:     {cur_dd:.2f}% (-{cur_dd_r:.1f}R)")
        print(f"[*] True MDD Trough:      {self.math_engine.mdd_trough_pct:.2f}% (-{mdd_r:.1f}R)")
        print(f"[*] Divisor:              {config.DEFAULT_DIVISOR}")
        print(f"[*] Target 1R Stake:      NGN {self.math_engine.peak_balance / config.DEFAULT_DIVISOR:,.2f}")
        print(f"[*] Target Odds Min:      {config.TARGET_ODDS_MIN:.2f}")
        print(f"[*] Telegram Milestone:   Every +{config.TELEGRAM_MILESTONE_STEP_PCT:.0f}% (Last: #{self.last_reported_milestone})")
        print("=" * 65 + "\n")

    def _check_and_send_milestones(self, total_bets: int, total_wins: int):
        """Checks if current peak balance has achieved new milestone steps."""
        if config.INITIAL_BALANCE <= 0:
            return

        gain_pct = ((self.math_engine.peak_balance - config.INITIAL_BALANCE) / config.INITIAL_BALANCE) * 100.0
        step = config.TELEGRAM_MILESTONE_STEP_PCT
        if step <= 0:
            step = 100.0

        current_milestone_tier = int(gain_pct // step)

        if current_milestone_tier > self.last_reported_milestone:
            for m in range(self.last_reported_milestone + 1, current_milestone_tier + 1):
                tier_gain = m * step
                win_rate = (total_wins / total_bets * 100.0) if total_bets > 0 else 0.0

                print(f"\n[TELEGRAM] 🚀 DISPATCHING MILESTONE ALERT #{m} (+{tier_gain:.1f}%)!")
                asyncio.create_task(self.telegram.notify_milestone(
                    milestone_num=m,
                    gain_pct=tier_gain,
                    current_balance=self.math_engine.current_balance,
                    peak_balance=self.math_engine.peak_balance,
                    total_bets=total_bets,
                    win_rate=win_rate,
                    mdd_trough=self.math_engine.mdd_trough_pct
                ))

            self.last_reported_milestone = current_milestone_tier
            self.db.update_last_milestone(current_milestone_tier)

    def _on_resolution(self, event: Dict[str, Any]):
        """Records EVERY Bristol race result to the DB, whether or not we bet on it."""
        try:
            final_order = event.get("final_order") or []
            won = event.get("won_markets") or []
            is_bristol = (event.get("playlist_id") == config.BRISTOL_PLAYLIST_ID) or (
                len(final_order) == 4 and any("place_" in m for m in won))
            eid = event.get("eblock_id")
            if is_bristol and eid is not None:
                self.db.record_race_result(str(eid), int(eid) if str(eid).isdigit() else None, final_order, won)
        except Exception as e:
            print(f"[!] Result ledger notice: {e}")

    async def _reconnect_stream(self, reason: str) -> bool:
        """Single, guarded page reload to restore the VirtusTec feed."""
        now = time.time()
        if now - self._last_reconnect_ts < 45:
            return False
        # Never reload while a race is in (or about to enter) its bet window
        if self.current_seconds_left is not None and 4 <= self.current_seconds_left <= 35:
            return False
        self._last_reconnect_ts = now
        print(f"[WATCHDOG] {reason} Reconnecting VirtusTec stream...")
        try:
            await self.browser_manager.navigate_to_bristol()
            self.ws_listener.attach_to_page(self.browser_manager.page)
        except Exception as stream_err:
            print(f"[WATCHDOG] Reconnect error: {stream_err}. Restoring browser session...")
            await self.browser_manager.restart_and_recover()
            self.ws_listener.attach_to_page(self.browser_manager.page)
        self.reconnect_requested = False
        print("[WATCHDOG] Stream reconnect complete.")
        return True

    async def run(self):
        if config.BOT_MODE == "LIVE" and self.math_engine.current_balance <= 0:
            print("\n" + "=" * 65)
            print("[CRITICAL ALERT] LIVE ACCOUNT IS CURRENTLY LIQUIDATED (Balance: NGN 0.00)")
            print("Please deposit real funds into SportyBet to resume.")
            print("=" * 65 + "\n")
            print("[*] Bot is paused awaiting capital. Press Ctrl+C to exit.")
            while True:
                await asyncio.sleep(60)

        if config.BOT_MODE == "PAPER" and self.math_engine.current_balance <= 0:
            dd_r = self.math_engine.get_current_drawdown_r()
            print(f"[*] [UNCONSTRAINED PAPER MODE ACTIVE] Current Drawdown is -{dd_r:.1f}R (Balance: NGN {self.math_engine.current_balance:,.2f}). Continuing unconstrained simulation to track true historical MDD!")

        # Startup notification
        await self.telegram.notify_startup(
            mode=config.BOT_MODE,
            balance=self.math_engine.current_balance,
            peak=self.math_engine.peak_balance,
            divisor=config.DEFAULT_DIVISOR,
            target_odds=config.TARGET_ODDS_MIN
        )

        # 1. Start browser & attach WS listener
        page = await self.browser_manager.start()
        self.ws_listener.attach_to_page(page)

        # 2. Navigate to Bristol Speedway
        try:
            await self.browser_manager.navigate_to_bristol()
        except Exception as e:
            await self.telegram.notify_error(str(e), "Initial navigation to Bristol Speedway")
            raise

        # If running LIVE, sync balance from platform
        if config.BOT_MODE == "LIVE":
            live_bal = await self.browser_manager.get_account_balance()
            if live_bal > 0:
                print(f"[BOT] Synced real live balance from platform: NGN {live_bal:,.2f}")
                if live_bal > self.math_engine.peak_balance:
                    self.math_engine.peak_balance = live_bal
                self.math_engine.current_balance = live_bal

        processed_races = set()
        races_since_last_hygiene = 0
        no_race_watchdog_ticks = 0

        # Restart recovery: bets left PENDING by a previous process get a settlement worker again
        for pb in self.db.get_pending_bets():
            print(f"[RECOVERY] Re-tracking pending bet #{pb['bet_id']} (Race #{pb['race_id']}, Runner #{pb['runner_num']})")
            processed_races.add(str(pb["race_id"]))
            asyncio.create_task(self._settle_bet_async(
                bet_id=pb["bet_id"],
                race_id=str(pb["race_id"]),
                target={"runner_num": pb["runner_num"], "runner_name": pb["runner_name"], "place_odd": pb["place_odd"]},
                stake=pb["stake"]
            ))

        print("\n[*] Starting continuous 2-minute race cycle monitoring...\n")

        while True:
            try:
                # 24/7 Heartbeat: Signal OS supervisor that engine is actively cycling
                try:
                    with open("/tmp/virtual_ratchet_heartbeat", "w") as hbf:
                        hbf.write(f"{time.time()}\n")
                except Exception:
                    pass

                # 24/7 WebSocket Stream Liveness Check: Self-heal disconnected socket (guarded, single path)
                if self.reconnect_requested or not self.ws_listener.is_stream_alive(max_idle_seconds=60.0):
                    reason = "Settlement worker requested refresh." if self.reconnect_requested else "WebSocket feed idle for >60s."
                    await self._reconnect_stream(reason)

                # 24/7 Browser Health Verification
                if not self.browser_manager.is_healthy():
                    print("[!] Browser connection lost or page closed. Recovering...")
                    await self.browser_manager.restart_and_recover()
                    self.ws_listener.attach_to_page(self.browser_manager.page)
                    no_race_watchdog_ticks = 0

                # 24/7 Memory Hygiene: Refresh page every 180 races (~6 hours) during idle window
                if races_since_last_hygiene >= 180:
                    try:
                        print("\n[*] [24/7 MAINTENANCE] Performing scheduled Chromium memory hygiene...")
                        await self.browser_manager.navigate_to_bristol()
                        races_since_last_hygiene = 0
                        no_race_watchdog_ticks = 0
                        print("[+] Maintenance complete! RAM flushed, continuing cycle.\n")
                    except Exception as m_err:
                        print(f"[!] Maintenance notice: {m_err}")

                # 3. Get upcoming race details
                race = await self.browser_manager.get_upcoming_race()
                if not race:
                    no_race_watchdog_ticks += 1
                    if no_race_watchdog_ticks == 15:  # ~30 seconds of missing race
                        print("[WATCHDOG] No upcoming race panel visible for 30s. Checking frame route...")
                        await self.browser_manager.ensure_bristol_route()
                    elif no_race_watchdog_ticks >= 45:  # ~90 seconds of missing race
                        print("[WATCHDOG] No race panels detected for 90s! Recovering browser and reloading session...")
                        await self.browser_manager.restart_and_recover()
                        self.ws_listener.attach_to_page(self.browser_manager.page)
                        no_race_watchdog_ticks = 0
                    await asyncio.sleep(2)
                    continue

                no_race_watchdog_ticks = 0

                race_id = race["race_id"]
                seconds_left = race["seconds_left"]
                self.current_seconds_left = seconds_left

                # If this race has already been bet or processed, wait
                if race_id in processed_races:
                    await asyncio.sleep(2)
                    continue

                # Display countdown update every 15s or when in final stretch
                if seconds_left % 15 == 0 or seconds_left <= 30:
                    print(f"[*] Race #{race_id} | Starts in {seconds_left:02d}s | Track: Bristol")

                # 4. Check if we are inside the execution window (between 6s and 25s before race)
                if config.BET_CUTOFF_BUFFER <= seconds_left <= config.BET_WINDOW_SECONDS:
                    print(f"\n" + "-" * 55)
                    print(f"[TRIGGER] Race #{race_id} in Bet Window ({seconds_left}s remaining)!")

                    # Log odds to terminal
                    for r in race["runners"]:
                        cand_mark = "(*)" if r["place_odd"] >= config.TARGET_ODDS_MIN else "   "
                        print(f"  {cand_mark} #{r['runner_num']} {r['runner_name']:<18} | WIN: {r['win_odd']:<4.2f} | PLACE: {r['place_odd']:<4.2f}")

                    # Run Odd Algo
                    analysis = self.odds_analyzer.analyze_race(race["runners"])
                    print(f"[DECISION] {analysis['decision']} - {analysis['reason']}")

                    chosen_num = analysis["target_runner"]["runner_num"] if analysis["target_runner"] else None

                    # Snapshot race and candidates to SQLite
                    self.db.record_race_snapshot(
                        race_id=race_id,
                        eblock_id=int(race_id) if race_id.isdigit() else None,
                        track_name="Bristol",
                        runners_data=race["runners"],
                        chosen_runner_num=chosen_num
                    )

                    # Execute Bet if Qualified
                    if analysis["decision"] == "BET":
                        target = analysis["target_runner"]

                        # Calculate Peak Ratchet Stake
                        try:
                            stake, is_all_in = self.math_engine.calculate_stake()
                        except AccountLiquidatedException as e:
                            print(f"\n[CRITICAL ALERT] {e}")
                            highest_gain = ((self.math_engine.peak_balance - config.INITIAL_BALANCE) / config.INITIAL_BALANCE * 100) if config.INITIAL_BALANCE > 0 else 0
                            await self.telegram.notify_bust(
                                current_balance=self.math_engine.current_balance,
                                peak_balance=self.math_engine.peak_balance,
                                highest_gain_pct=highest_gain,
                                total_bets=self.state.get("total_bets", 0),
                                mdd_trough=self.math_engine.mdd_trough_pct
                            )
                            print("[CRITICAL] Bot halted to protect remaining capital.\n")
                            break

                        dd_pct = self.math_engine.get_current_drawdown_pct()

                        is_paper_bet = (config.BOT_MODE == "PAPER")

                        bet_info = {
                            "race_id": race_id,
                            "runner_num": target["runner_num"],
                            "runner_name": target["runner_name"],
                            "place_odd": target["place_odd"],
                            "stake": stake,
                            "balance_before": self.math_engine.current_balance,
                            "peak_before": self.math_engine.peak_balance,
                            "drawdown_pct": dd_pct,
                            "mdd_trough_pct": self.math_engine.mdd_trough_pct,
                            "is_all_in": is_all_in
                        }

                        # Record bet as pending in DB
                        bet_id = self.db.record_bet_placed(bet_info)

                        mode_label = "[PAPER/SIM]" if is_paper_bet else "[LIVE]"
                        print(f"\n[EXECUTING BET {mode_label}] Staking NGN {stake:,.2f} on Runner #{target['runner_num']} ({target['runner_name']}) @ {target['place_odd']:.2f}")
                        if is_all_in:
                            print(f"[!] ALL-IN MODE: Full remaining balance risked!")

                        if is_paper_bet:
                            bet_success = True
                            print(f"[+] Paper bet registered! Awaiting live race finish via WebSocket...")
                        else:
                            bet_success = await self.browser_manager.execute_place_bet(
                                runner_element=target["element"],
                                stake_amount=stake
                            )

                        if bet_success:
                            processed_races.add(race_id)
                            # Decoupled Asynchronous Settlement: Hand off to concurrent task so main loop never blocks
                            asyncio.create_task(
                                self._settle_bet_async(
                                    bet_id=bet_id,
                                    race_id=race_id,
                                    target=target,
                                    stake=stake
                                )
                            )
                        else:
                            print(f"[!] Failed to place bet in betslip for race #{race_id}. Skipping.")
                            processed_races.add(race_id)

                    else:
                        # Skipped race
                        processed_races.add(race_id)
                        print(f"[+] Race #{race_id} skipped. Waiting for next race in cycle...\n")

                # Keep memory clean
                if len(processed_races) > 100:
                    processed_races = set(list(processed_races)[-50:])
                    races_since_last_hygiene += 50

                await asyncio.sleep(2)

            except Exception as loop_err:
                print(f"[!] Error in main loop: {loop_err}")
                await self.telegram.notify_error(str(loop_err), "Main loop execution")
                await asyncio.sleep(5)

    async def _settle_bet_async(self, bet_id: int, race_id: str, target: Dict[str, Any], stake: float):
        """Asynchronously waits for race resolution and settles the bet without blocking upcoming races."""
        target_eblock = int(race_id) if race_id.isdigit() else None
        print(f"[*] [SETTLEMENT WORKER] Tracking live resolution for Race #{race_id} (Runner #{target['runner_num']})...")

        # Tier 0: result may already be in the ledger (e.g. recovered after a restart)
        resolved_event = None
        stored = self.db.get_race_result(race_id)
        if stored:
            resolved_event = stored

        # Tier 1: wait on the live feed
        if not resolved_event:
            resolved_event = await self.ws_listener.wait_for_resolution(
                target_eblock_id=target_eblock,
                timeout=80.0
            )

        # Tier 2: ask the main loop for a guarded reconnect (it never reloads inside a bet window), then keep waiting
        if not resolved_event:
            print(f"[*] [SETTLEMENT WORKER] Race #{race_id} result not received in 80s. Requesting stream reconnect...")
            self.reconnect_requested = True
            resolved_event = await self.ws_listener.wait_for_resolution(
                target_eblock_id=target_eblock,
                timeout=100.0
            )
            if not resolved_event:
                stored = self.db.get_race_result(race_id)
                if stored:
                    resolved_event = stored

        if resolved_event:
            won_markets = resolved_event["won_markets"]
            final_order = resolved_event["final_order"]

            # Settle race in DB
            self.db.settle_race(
                race_id=race_id,
                eblock_id=resolved_event["eblock_id"],
                final_order=final_order,
                won_markets=won_markets
            )

            # Dual-verification of win: Place market won OR runner in top 2 finish positions
            place_key = f"place_{target['runner_num']}"
            is_in_won_markets = place_key in won_markets
            is_in_top_two = (len(final_order) >= 2 and str(target['runner_num']) in [str(final_order[0]), str(final_order[1])])
            is_win = is_in_won_markets or is_in_top_two

            res = self.math_engine.evaluate_result(
                is_win=is_win,
                odds=target["place_odd"],
                stake=stake
            )

            # Settle bet in DB
            self.db.settle_bet(
                bet_id=bet_id,
                result=res["result"],
                pnl=res["pnl"],
                balance_after=res["balance_after"],
                peak_after=res["peak_after"],
                drawdown_pct=res["drawdown_pct"],
                mdd_pct=res["mdd_trough_pct"]
            )

            # Update Account State Singleton
            self.db.update_account_state(
                current_balance=res["balance_after"],
                peak_balance=res["peak_after"],
                max_drawdown=res["mdd_trough_pct"],
                wins=1 if is_win else 0,
                losses=0 if is_win else 1
            )

            # Check and dispatch Telegram Milestones
            updated_state = self.db.load_account_state()
            self._check_and_send_milestones(
                total_bets=updated_state["total_bets"],
                total_wins=updated_state["total_wins"]
            )

            # Check if balance hit 0 (Bust condition)
            if config.BOT_MODE == "LIVE" and res["balance_after"] <= 0:
                highest_gain = ((res["peak_after"] - config.INITIAL_BALANCE) / config.INITIAL_BALANCE * 100) if config.INITIAL_BALANCE > 0 else 0
                await self.telegram.notify_bust(
                    current_balance=0.0,
                    peak_balance=res["peak_after"],
                    highest_gain_pct=highest_gain,
                    total_bets=updated_state["total_bets"],
                    mdd_trough=res["mdd_trough_pct"]
                )
                print("\n[CRITICAL] LIVE account liquidated. Bot halted.")
            elif config.BOT_MODE == "PAPER" and res["balance_after"] <= 0:
                dd_r = self.math_engine.get_current_drawdown_r()
                print(f" ⚠️ [UNCONSTRAINED PAPER MODE] Drawdown extended: {res['drawdown_pct']:.2f}% (-{dd_r:.1f}R). Continuing simulation...")

            # Print Results Banner with R-multiples
            r_mult = (target["place_odd"] - 1.0) if is_win else -1.0
            print("\n" + "=" * 55)
            if is_win:
                print(f" 🎉 [WIN +{r_mult:.2f}R] Race #{race_id} Runner #{target['runner_num']} placed! PnL: +NGN {res['pnl']:,.2f}")
            else:
                print(f" ❌ [LOSS -1.00R] Race #{race_id} Runner #{target['runner_num']} did not place. PnL: -NGN {abs(res['pnl']):,.2f}")

            print(f"    Current Balance:  NGN {res['balance_after']:,.2f}")
            print(f"    Peak Balance:     NGN {res['peak_after']:,.2f} {'(NEW HIGH-WATER MARK!)' if res['is_new_peak'] else ''}")
            r_step = 100.0 / config.DEFAULT_DIVISOR
            dd_r = self.math_engine.get_current_drawdown_r()
            mdd_r = res['mdd_trough_pct'] / r_step if r_step > 0 else 0
            print(f"    Current Drawdown: {res['drawdown_pct']:.2f}% (-{dd_r:.1f}R)")
            print(f"    True MDD Trough:  {res['mdd_trough_pct']:.2f}% (-{mdd_r:.1f}R)")
            print("=" * 55 + "\n")

        else:
            print(f"[!] WebSocket resolution timed out for race #{race_id} after 90s.")
            # Fallback resolution for LIVE mode: sync live platform balance
            if config.BOT_MODE == "LIVE":
                live_bal = await self.browser_manager.get_account_balance()
                if live_bal > 0:
                    is_win = (live_bal >= (self.math_engine.current_balance + (stake * (target["place_odd"] - 1.0) * 0.5)))
                    print(f"[*] Live platform balance fallback check: NGN {live_bal:,.2f} (Inferred: {'WIN' if is_win else 'LOSS'})")
                    res = self.math_engine.evaluate_result(is_win=is_win, odds=target["place_odd"], stake=stake)
                    self.db.settle_bet(bet_id=bet_id, result=res["result"], pnl=res["pnl"], balance_after=res["balance_after"], peak_after=res["peak_after"], drawdown_pct=res["drawdown_pct"], mdd_pct=res["mdd_trough_pct"])
                    self.db.update_account_state(current_balance=res["balance_after"], peak_balance=res["peak_after"], max_drawdown=res["mdd_trough_pct"], wins=1 if is_win else 0, losses=0 if is_win else 1)
                else:
                    print(f"[!] Live platform balance unverified. Marking bet #{bet_id} as VOID to preserve capital.")
                    self.db.settle_bet(bet_id=bet_id, result="VOID", pnl=0.0, balance_after=self.math_engine.current_balance, peak_after=self.math_engine.peak_balance, drawdown_pct=self.math_engine.get_current_drawdown_pct(), mdd_pct=self.math_engine.mdd_trough_pct)
            elif config.BOT_MODE == "PAPER":
                print(f"[*] [UNRESOLVED RACE #{race_id}] Packet missed after 90s.")
                print(f"    Settling bet #{bet_id} as VOID (stake refunded, NGN 0.00 PnL) to preserve ledger integrity.")
                self.db.settle_bet(
                    bet_id=bet_id,
                    result="VOID",
                    pnl=0.0,
                    balance_after=self.math_engine.current_balance,
                    peak_after=self.math_engine.peak_balance,
                    drawdown_pct=self.math_engine.get_current_drawdown_pct(),
                    mdd_pct=self.math_engine.mdd_trough_pct
                )

async def main():
    bot = VirtualRatchetBot()
    try:
        await bot.run()
    finally:
        print("\n[BOT] Cleaning up browser and sub-processes...")
        try:
            await bot.browser_manager.close()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Bot stopped by user.")
