import sqlite3
import pandas as pd
import config
from db.journal import DatabaseJournal

def generate_report():
    # Ensure database schema is initialized
    db = DatabaseJournal(config.DB_FILE)
    conn = sqlite3.connect(config.DB_FILE, timeout=30.0)

    print("=" * 70)
    print("      VIRTUAL RATCHET: MDD & PERFORMANCE ANALYTICS REPORT")
    print("=" * 70)

    # 1. Account state summary
    state = conn.execute("SELECT * FROM account_state WHERE id = 1").fetchone()
    if state and state[4] > 0:
        r_step = 100.0 / config.DEFAULT_DIVISOR
        mdd_r = state[3] / r_step if r_step > 0 else 0.0
        print("\n--- 1. Current Account Health ---")
        print(f"Current Balance:        NGN {state[1]:,.2f}")
        print(f"Peak Balance Achieved:  NGN {state[2]:,.2f}")
        print(f"True Max Drawdown (MDD):{state[3]:.2f}% (-{mdd_r:.1f}R)")
        print(f"Total Bets Settled:     {state[4]}")
        print(f"Wins:                   {state[5]}")
        print(f"Losses:                 {state[6]}")
        settled = (state[5] + state[6])
        win_rate = (state[5] / settled * 100) if settled > 0 else 0.0
        print(f"Win Rate (Settled):     {win_rate:.2f}%\n")
    else:
        print("\nNo bets settled yet. Run the bot for a few races to build journal data.\n")

    # 2. Peak-by-Peak Analysis
    try:
        peaks_query = """
        SELECT
            peak_before as Peak,
            MIN(balance_after) as Deepest_Trough_Balance,
            MAX(drawdown_pct) as Max_Drawdown_Pct,
            COUNT(*) as Bets_During_This_Peak
        FROM bets
        WHERE result IN ('WIN', 'LOSS')
        GROUP BY peak_before
        ORDER BY peak_before ASC
        """
        peaks_df = pd.read_sql_query(peaks_query, conn)
        if not peaks_df.empty:
            r_step = 100.0 / config.DEFAULT_DIVISOR
            peaks_df["Drawdown_In_R"] = peaks_df["Max_Drawdown_Pct"].apply(lambda dd: f"-{dd / r_step:.1f}R")
            peaks_df["Peak"] = peaks_df["Peak"].apply(lambda p: f"NGN {p:,.2f}")
            peaks_df["Deepest_Trough_Balance"] = peaks_df["Deepest_Trough_Balance"].apply(lambda b: f"NGN {b:,.2f}")
            peaks_df["Max_Drawdown_Pct"] = peaks_df["Max_Drawdown_Pct"].apply(lambda dd: f"{dd:.2f}%")
            print("--- 2. Peak-by-Peak Trough Breakdown (How deep we dropped from each Peak) ---")
            print(peaks_df.to_string(index=False))
            print("\n")
    except Exception as e:
        pass

    # 3. Candidates Analysis (What happened to the lesser >= 2.80 odds?)
    try:
        cand_df = pd.read_sql_query("""
            SELECT
                race_id,
                runner_num,
                runner_name,
                place_odd,
                was_chosen,
                did_place,
                finish_rank
            FROM candidates_journal
            WHERE did_place IS NOT NULL
            ORDER BY race_id DESC, place_odd DESC
        """, conn)

        if not cand_df.empty:
            print("--- 3. Candidate Comparison Journal (High vs Lesser >= 2.80 Odds) ---")
            print(cand_df.head(15).to_string(index=False))

            chosen = cand_df[cand_df["was_chosen"] == 1]
            lesser = cand_df[cand_df["was_chosen"] == 0]

            chosen_wr = (chosen["did_place"].sum() / len(chosen) * 100) if len(chosen) > 0 else 0
            lesser_wr = (lesser["did_place"].sum() / len(lesser) * 100) if len(lesser) > 0 else 0

            print("\n--- Strategy Win-Rate Comparison ---")
            print(f"Chosen (Highest Odd) Placed: {chosen['did_place'].sum()}/{len(chosen)} ({chosen_wr:.1f}%)")
            print(f"Lesser (Alternative) Placed: {lesser['did_place'].sum()}/{len(lesser)} ({lesser_wr:.1f}%)")
            print("\n")
    except Exception:
        pass

    # 4. Multi-Divisor Simulation (What would have happened with Divisor 10, 15, 20?)
    try:
        cur = conn.cursor()
        cur.execute("SELECT race_id, runner_num, place_odd, result FROM bets WHERE result IN ('WIN', 'LOSS') ORDER BY bet_id ASC")
        rows = cur.fetchall()

        if len(rows) >= 3:
            print("--- 4. Multi-Divisor MDD Safety Simulation (Replaying Same Races) ---")
            divisors = [10.0, 15.0, 20.0, 25.0]
            sim_results = []
            for d in divisors:
                bal = config.INITIAL_BALANCE
                pk = config.INITIAL_BALANCE
                mdd = 0.0
                busted = False
                for r_id, num, odd, res in rows:
                    if bal <= 0:
                        busted = True
                        break
                    stk = round(pk / d, 2)
                    stk = stk if bal >= stk else bal
                    if res == "WIN":
                        bal = round(bal + stk * (odd - 1.0), 2)
                        pk = max(pk, bal)
                    else:
                        bal = round(max(0.0, bal - stk), 2)
                    dd = ((pk - bal) / pk * 100.0) if pk > 0 else 0.0
                    mdd = max(mdd, dd)

                sim_results.append({
                    "Divisor": f"{d:.0f}",
                    "Final Balance": f"NGN {bal:,.2f}",
                    "Peak Balance": f"NGN {pk:,.2f}",
                    "Max MDD Trough": f"{mdd:.1f}%",
                    "Liquidated?": "YES (BUST)" if busted else "NO"
                })

            print(pd.DataFrame(sim_results).to_string(index=False))
            print("\n")
    except Exception:
        pass

    conn.close()
    print("=" * 70 + "\n")

if __name__ == "__main__":
    generate_report()
