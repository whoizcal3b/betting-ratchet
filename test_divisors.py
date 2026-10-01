import sqlite3
import pandas as pd
from typing import List, Dict, Any
import config

def simulate_divisor_on_journal(divisor: float, initial_balance: float = 1000.0) -> Dict[str, Any]:
    """
    Replays the exact recorded historical bets from the database against a specific divisor
    to compute its High-Water Mark peak, final balance, and True Maximum Drawdown (MDD) Trough.
    """
    conn = sqlite3.connect(config.DB_FILE)
    cur = conn.cursor()

    # Query all settled bets in chronological order
    cur.execute("""
        SELECT
            b.race_id,
            b.runner_num,
            b.place_odd,
            b.result
        FROM bets b
        WHERE b.result IN ('WIN', 'LOSS')
        ORDER BY b.bet_id ASC
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return {
            "divisor": divisor,
            "total_bets": 0,
            "final_balance": initial_balance,
            "peak_balance": initial_balance,
            "mdd_trough_pct": 0.0,
            "busted": False
        }

    balance = initial_balance
    peak = initial_balance
    max_mdd_trough = 0.0
    busted = False

    for race_id, runner_num, odd, result in rows:
        if balance <= 0:
            busted = True
            break

        # Calculate stake: Peak / Divisor
        target_stake = round(peak / divisor, 2)
        stake = target_stake if balance >= target_stake else balance

        if result == "WIN":
            pnl = round(stake * (odd - 1.0), 2)
            balance = round(balance + pnl, 2)
            if balance > peak:
                peak = balance
        else:
            pnl = -stake
            balance = round(max(0.0, balance - stake), 2)

        # Calculate drawdown from the current peak
        drawdown_pct = ((peak - balance) / peak * 100.0) if peak > 0 else 0.0
        if drawdown_pct > max_mdd_trough:
            max_mdd_trough = drawdown_pct

    return {
        "divisor": divisor,
        "total_bets": len(rows),
        "final_balance": balance,
        "peak_balance": peak,
        "return_pct": ((balance - initial_balance) / initial_balance * 100.0),
        "peak_return_pct": ((peak - initial_balance) / initial_balance * 100.0),
        "mdd_trough_pct": max_mdd_trough,
        "busted": (balance <= 0)
    }

def compare_divisors():
    print("=" * 70)
    print("   VIRTUAL RATCHET: MULTI-DIVISOR MDD COMPARISON SIMULATOR")
    print("=" * 70)

    divisors_to_test = [10.0, 15.0, 20.0, 25.0, 30.0]
    results = []

    for d in divisors_to_test:
        res = simulate_divisor_on_journal(divisor=d, initial_balance=config.INITIAL_BALANCE)
        if res["total_bets"] == 0:
            print("[*] No settled bets found in journal.db yet.")
            print("    Run the bot in PAPER or LIVE mode for a few races to build journal data.")
            print("=" * 70)
            return
        results.append(res)

    df = pd.DataFrame(results)
    df = df[["divisor", "total_bets", "final_balance", "peak_balance", "return_pct", "mdd_trough_pct", "busted"]]
    df.columns = ["Divisor", "Bets", "Final Balance", "Peak Balance", "Return %", "Max MDD %", "Busted?"]

    print(df.to_string(index=False))
    print("=" * 70 + "\n")

if __name__ == "__main__":
    compare_divisors()
