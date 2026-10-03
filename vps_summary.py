import sqlite3
import subprocess
import os
import sys

def main():
    print("=" * 65)
    print("       VIRTUAL RATCHET BOT - 24H VPS PERFORMANCE AUDIT")
    print("=" * 65)

    # 1. Check systemd service log file
    log_file = "vps_service.log"
    if os.path.exists(log_file):
        log_size_kb = os.path.getsize(log_file) / 1024
        print(f"[+] Found '{log_file}' ({log_size_kb:.1f} KB).")

    # 2. Check Database
    db_file = "journal.db"
    if not os.path.exists(db_file):
        print(f"[!] Database file '{db_file}' not found in current directory.")
        return

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query account state
    try:
        state = cursor.execute("SELECT * FROM account_state WHERE id = 1").fetchone()
    except Exception as e:
        state = None

    # Query races count
    try:
        total_races = cursor.execute("SELECT COUNT(*) FROM races").fetchone()[0]
        resolved_races = cursor.execute("SELECT COUNT(*) FROM races WHERE status = 'RESOLVED'").fetchone()[0]
    except Exception:
        total_races = 0
        resolved_races = 0

    # Query bets
    try:
        cursor.execute("SELECT * FROM bets ORDER BY bet_id ASC")
        bets = cursor.fetchall()
    except Exception:
        bets = []

    total_bets = len(bets)
    wins = [b for b in bets if b["result"] == "WIN"]
    losses = [b for b in bets if b["result"] == "LOSS"]
    voids = [b for b in bets if b["result"] == "VOID"]
    win_count = len(wins)
    loss_count = len(losses)
    void_count = len(voids)
    settled_count = win_count + loss_count
    win_rate = (win_count / settled_count * 100) if settled_count > 0 else 0.0

    print("\n" + "-" * 65)
    print("                      ACCOUNT SUMMARY")
    print("-" * 65)

    if state:
        curr_bal = state["current_balance"]
        peak_bal = state["peak_balance"]
        mdd_val = state["max_drawdown_trough"]
        print(f"  Current Balance : NGN {curr_bal:,.2f}")
        print(f"  Peak Balance    : NGN {peak_bal:,.2f}")
        print(f"  Max Drawdown    : {mdd_val:.1f}%")
        print(f"  Last Updated    : {state['updated_at']}")
    elif bets:
        curr_bal = bets[-1]["balance_after"]
        peak_bal = max(b["peak_after"] for b in bets)
        max_dd = max(b["drawdown_pct"] for b in bets)
        print(f"  Current Balance : NGN {curr_bal:,.2f}")
        print(f"  Peak Balance    : NGN {peak_bal:,.2f}")
        print(f"  Max Drawdown    : {max_dd:.1f}%")

    print("\n" + "-" * 65)
    print("                    STATISTICAL METRICS")
    print("-" * 65)
    print(f"  Total Races Evaluated : {total_races} (Resolved: {resolved_races})")
    print(f"  Total Bets Placed     : {total_bets}")
    print(f"  Wins / Losses / Voids : {win_count} Wins / {loss_count} Losses ({void_count} Void)")
    print(f"  Win Rate (Settled)    : {win_rate:.2f}%")

    # Streaks
    max_win_streak = 0
    max_loss_streak = 0
    cur_win_streak = 0
    cur_loss_streak = 0
    for b in bets:
        if b["result"] == "WIN":
            cur_win_streak += 1
            cur_loss_streak = 0
            if cur_win_streak > max_win_streak:
                max_win_streak = cur_win_streak
        elif b["result"] == "LOSS":
            cur_loss_streak += 1
            cur_win_streak = 0
            if cur_loss_streak > max_loss_streak:
                max_loss_streak = cur_loss_streak
        # VOID bets do not interrupt win/loss streaks

    print(f"  Max Win Streak        : {max_win_streak}")
    print(f"  Max Loss Streak       : {max_loss_streak}")

    # Export CSV of all bets
    csv_file = "vps_bets.csv"
    try:
        import csv
        if bets:
            keys = bets[0].keys()
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(keys)
                for b in bets:
                    writer.writerow([b[k] for k in keys])
            print(f"\n[+] Exported {len(bets)} bets to '{csv_file}'")
    except Exception as e:
        print(f"[!] Warning exporting CSV: {e}")

    # Print Last 10 Bets
    if bets:
        print("\n" + "-" * 65)
        print("                 LAST 10 SETTLED BETS")
        print("-" * 65)
        print(f"{'ID':<5} {'Race ID':<10} {'Runner':<8} {'Odds':<6} {'Stake':<8} {'Result':<6} {'Balance After':<14} {'DD%':<6}")
        print("-" * 65)
        for b in bets[-10:]:
            r_num = f"#{b['runner_num']}"
            res = b['result']
            print(f"{b['bet_id']:<5} {str(b['race_id']):<10} {r_num:<8} {b['place_odd']:<6.2f} {b['stake']:<8.2f} {res:<6} NGN {b['balance_after']:<10.2f} {b['drawdown_pct']:<5.1f}%")

    print("\n" + "=" * 65)
    print("  FILES READY FOR EXPORT:")
    print(f"  1. {log_file}  (Full systemd console outputs)")
    print(f"  2. {csv_file}    (Full bet-by-bet ledger)")
    print(f"  3. {db_file}       (Full SQLite database)")
    print("=" * 65)
    conn.close()

if __name__ == "__main__":
    main()
