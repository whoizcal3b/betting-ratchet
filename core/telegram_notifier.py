import asyncio
import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any
import config

class TelegramNotifier:
    def __init__(self, bot_token: str = config.TELEGRAM_BOT_TOKEN, chat_id: str = config.TELEGRAM_CHAT_ID):
        self.bot_token = bot_token.strip() if bot_token else ""
        self.chat_id = chat_id.strip() if chat_id else ""
        self.is_enabled = bool(self.bot_token and self.chat_id)

        if self.is_enabled:
            print(f"[TELEGRAM] Notifications active for Chat ID: {self.chat_id}")
        else:
            print("[TELEGRAM] Note: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured in .env (alerts disabled).")

    async def send_message(self, text: str) -> bool:
        if not self.is_enabled:
            return False

        def _post():
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                payload = {
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.status == 200
            except Exception as e:
                print(f"[TELEGRAM] Failed to send alert: {e}")
                return False

        return await asyncio.to_thread(_post)

    async def notify_milestone(self, milestone_num: int, gain_pct: float, current_balance: float, peak_balance: float, total_bets: int, win_rate: float, mdd_trough: float):
        if not config.TELEGRAM_NOTIFY_MILESTONES:
            return

        msg = (
            f"🚀 <b>VIRTUAL RATCHET: MILESTONE #{milestone_num} REACHED!</b>\n\n"
            f"📈 <b>Peak Growth:</b> +{gain_pct:,.1f}%\n"
            f"💰 <b>Current Balance:</b> ₦{current_balance:,.2f}\n"
            f"🏔 <b>Peak Balance:</b> ₦{peak_balance:,.2f}\n"
            f"🎯 <b>Total Bets:</b> {total_bets} (Win Rate: {win_rate:.1f}%)\n"
            f"📉 <b>True MDD Trough:</b> {mdd_trough:.2f}%\n\n"
            f"<i>Next 1R Stake pegged at: ₦{peak_balance / config.DEFAULT_DIVISOR:,.2f}</i>"
        )
        await self.send_message(msg)

    async def notify_bust(self, current_balance: float, peak_balance: float, highest_gain_pct: float, total_bets: int, mdd_trough: float):
        if not config.TELEGRAM_NOTIFY_BUST:
            return

        msg = (
            f"🚨 <b>VIRTUAL RATCHET: ACCOUNT BUSTED / LIQUIDATED!</b>\n\n"
            f"💔 <b>Balance Depleted:</b> ₦{current_balance:,.2f}\n"
            f"🏔 <b>Highest Peak Reached:</b> ₦{peak_balance:,.2f} (+{highest_gain_pct:,.1f}%)\n"
            f"📉 <b>Max Drawdown Trough:</b> {mdd_trough:.2f}%\n"
            f"🛑 <b>Total Bets Executed:</b> {total_bets}\n\n"
            f"⚠️ <b>Action Required:</b> Account cannot place further bets. Please inject new capital to restart the ratchet."
        )
        await self.send_message(msg)

    async def notify_error(self, error_msg: str, context_details: str = ""):
        if not config.TELEGRAM_NOTIFY_ERRORS:
            return

        msg = (
            f"⚠️ <b>VIRTUAL RATCHET: ERROR ALERT</b>\n\n"
            f"<b>Context:</b> {context_details}\n"
            f"<b>Error:</b> <code>{error_msg[:300]}</code>\n\n"
            f"<i>Bot is attempting automatic recovery for the next cycle.</i>"
        )
        await self.send_message(msg)

    async def notify_startup(self, mode: str, balance: float, peak: float, divisor: float, target_odds: float):
        msg = (
            f"🤖 <b>VIRTUAL RATCHET BOT STARTED</b>\n\n"
            f"⚙️ <b>Mode:</b> {mode}\n"
            f"💰 <b>Current Balance:</b> ₦{balance:,.2f}\n"
            f"🏔 <b>Peak Balance:</b> ₦{peak:,.2f}\n"
            f"➗ <b>Divisor:</b> {divisor}\n"
            f"🎯 <b>Target Odds:</b> ≥{target_odds:.2f}\n"
            f"🏁 <b>Target Market:</b> Speedway Bristol (2-min cycle)"
        )
        await self.send_message(msg)
