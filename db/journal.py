import sqlite3
import json
import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

class DatabaseJournal:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """Thread-safe and process-safe connection context with auto-close and 30s busy timeout."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000;")
        try:
            yield conn
        finally:
            conn.close()

    def check_integrity(self) -> bool:
        """Verifies SQLite B-tree integrity for 24/7 data safety."""
        with self._get_conn() as conn:
            res = conn.execute("PRAGMA integrity_check;").fetchone()
            return bool(res and res[0] == "ok")

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # 24/7 high concurrency, zero-locking, and bounded WAL settings
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA wal_autocheckpoint=1000;")

            # 1. Races table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS races (
                race_id TEXT PRIMARY KEY,
                eblock_id INTEGER,
                track_name TEXT,
                start_time TEXT,
                status TEXT,
                final_order TEXT,
                won_markets TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. Race odds table (all 4 runners)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS race_odds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                race_id TEXT,
                runner_num INTEGER,
                runner_name TEXT,
                win_odd REAL,
                place_odd REAL,
                is_candidate INTEGER,
                is_chosen INTEGER,
                FOREIGN KEY (race_id) REFERENCES races(race_id)
            )
            """)

            # 3. Bets table (Full PnL, Peak, and Drawdown ledger)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                race_id TEXT,
                runner_num INTEGER,
                runner_name TEXT,
                place_odd REAL,
                stake REAL,
                balance_before REAL,
                peak_before REAL,
                result TEXT,            -- 'WIN', 'LOSS', 'SKIPPED'
                pnl REAL,
                balance_after REAL,
                peak_after REAL,
                drawdown_pct REAL,
                mdd_trough_pct REAL,
                is_all_in INTEGER,
                placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settled_at TIMESTAMP,
                FOREIGN KEY (race_id) REFERENCES races(race_id)
            )
            """)

            # 4. Candidates Journal (Tracking what happened to the lesser >= 2.80 odds)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                race_id TEXT,
                runner_num INTEGER,
                runner_name TEXT,
                place_odd REAL,
                was_chosen INTEGER,
                did_place INTEGER,      -- 1 if runner finished top 2, 0 otherwise
                finish_rank INTEGER,
                FOREIGN KEY (race_id) REFERENCES races(race_id)
            )
            """)

            # 5. Account state singleton
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_state (
                id INTEGER PRIMARY KEY,
                current_balance REAL,
                peak_balance REAL,
                max_drawdown_trough REAL,
                total_bets INTEGER,
                total_wins INTEGER,
                total_losses INTEGER,
                last_reported_milestone INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Ensure last_reported_milestone column exists if upgrading existing DB
            try:
                cursor.execute("ALTER TABLE account_state ADD COLUMN last_reported_milestone INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            conn.commit()

    def load_account_state(self, initial_balance: float = 1000.0) -> Dict[str, Any]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM account_state WHERE id = 1").fetchone()
            if row:
                return dict(row)
            else:
                # Initialize state
                conn.execute("""
                INSERT INTO account_state (id, current_balance, peak_balance, max_drawdown_trough, total_bets, total_wins, total_losses, last_reported_milestone)
                VALUES (1, ?, ?, 0.0, 0, 0, 0, 0)
                """, (initial_balance, initial_balance))
                conn.commit()
                return {
                    "id": 1,
                    "current_balance": initial_balance,
                    "peak_balance": initial_balance,
                    "max_drawdown_trough": 0.0,
                    "total_bets": 0,
                    "total_wins": 0,
                    "total_losses": 0,
                    "last_reported_milestone": 0
                }

    def update_account_state(self, current_balance: float, peak_balance: float, max_drawdown: float, wins: int, losses: int):
        with self._get_conn() as conn:
            conn.execute("""
            UPDATE account_state
            SET current_balance = ?,
                peak_balance = ?,
                max_drawdown_trough = ?,
                total_bets = total_bets + 1,
                total_wins = total_wins + ?,
                total_losses = total_losses + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """, (current_balance, peak_balance, max_drawdown, wins, losses))
            conn.commit()

    def update_last_milestone(self, milestone_num: int):
        with self._get_conn() as conn:
            conn.execute("""
            UPDATE account_state
            SET last_reported_milestone = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """, (milestone_num,))
            conn.commit()

    def record_race_snapshot(self, race_id: str, eblock_id: Optional[int], track_name: str, runners_data: List[Dict[str, Any]], chosen_runner_num: Optional[int]):
        with self._get_conn() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO races (race_id, eblock_id, track_name, status)
            VALUES (?, ?, ?, 'PENDING')
            """, (race_id, eblock_id, track_name))

            for r in runners_data:
                is_cand = 1 if r["place_odd"] >= 2.80 else 0
                is_chosen = 1 if (chosen_runner_num is not None and r["runner_num"] == chosen_runner_num) else 0
                conn.execute("""
                INSERT INTO race_odds (race_id, runner_num, runner_name, win_odd, place_odd, is_candidate, is_chosen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (race_id, r["runner_num"], r["runner_name"], r["win_odd"], r["place_odd"], is_cand, is_chosen))

                # If candidate, record in candidates journal
                if is_cand:
                    conn.execute("""
                    INSERT INTO candidates_journal (race_id, runner_num, runner_name, place_odd, was_chosen, did_place, finish_rank)
                    VALUES (?, ?, ?, ?, ?, NULL, NULL)
                    """, (race_id, r["runner_num"], r["runner_name"], r["place_odd"], is_chosen))
            conn.commit()

    def record_bet_placed(self, bet_info: Dict[str, Any]) -> int:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO bets (
                race_id, runner_num, runner_name, place_odd, stake,
                balance_before, peak_before, result, pnl,
                balance_after, peak_after, drawdown_pct, mdd_trough_pct, is_all_in
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', 0, ?, ?, ?, ?, ?)
            """, (
                bet_info["race_id"],
                bet_info["runner_num"],
                bet_info["runner_name"],
                bet_info["place_odd"],
                bet_info["stake"],
                bet_info["balance_before"],
                bet_info["peak_before"],
                bet_info["balance_before"],
                bet_info["peak_before"],
                bet_info["drawdown_pct"],
                bet_info["mdd_trough_pct"],
                1 if bet_info.get("is_all_in") else 0
            ))
            conn.commit()
            return cur.lastrowid

    def settle_race(self, race_id: str, eblock_id: int, final_order: List[str], won_markets: List[str]):
        with self._get_conn() as conn:
            conn.execute("""
            UPDATE races
            SET status = 'RESOLVED',
                eblock_id = ?,
                final_order = ?,
                won_markets = ?
            WHERE race_id = ?
            """, (eblock_id, json.dumps(final_order), json.dumps(won_markets), race_id))

            for rank_0, runner_str in enumerate(final_order):
                runner_num = int(runner_str)
                rank = rank_0 + 1
                did_place = 1 if rank <= 2 else 0

                conn.execute("""
                UPDATE candidates_journal
                SET did_place = ?,
                    finish_rank = ?
                WHERE race_id = ? AND runner_num = ?
                """, (did_place, rank, race_id, runner_num))

            conn.commit()

    def settle_bet(self, bet_id: int, result: str, pnl: float, balance_after: float, peak_after: float, drawdown_pct: float, mdd_pct: float):
        with self._get_conn() as conn:
            conn.execute("""
            UPDATE bets
            SET result = ?,
                pnl = ?,
                balance_after = ?,
                peak_after = ?,
                drawdown_pct = ?,
                mdd_trough_pct = ?,
                settled_at = CURRENT_TIMESTAMP
            WHERE bet_id = ?
            """, (result, pnl, balance_after, peak_after, drawdown_pct, mdd_pct, bet_id))
            conn.commit()

    def record_race_result(self, race_id: str, eblock_id: Optional[int], final_order: List[str], won_markets: List[str]):
        """Stores the result of EVERY Bristol race seen on the feed (bet on or not), creating the row if needed.
        This is the master chronological ledger used for gap detection and restart recovery."""
        with self._get_conn() as conn:
            conn.execute("""
            INSERT OR IGNORE INTO races (race_id, eblock_id, track_name, status)
            VALUES (?, ?, 'Bristol', 'PENDING')
            """, (race_id, eblock_id))
            conn.commit()
        self.settle_race(race_id=race_id, eblock_id=eblock_id, final_order=final_order, won_markets=won_markets)

    def get_race_result(self, race_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT eblock_id, final_order, won_markets FROM races WHERE race_id = ? AND status = 'RESOLVED'",
                (race_id,)
            ).fetchone()
            if not row or not row["final_order"]:
                return None
            return {
                "eblock_id": row["eblock_id"],
                "final_order": json.loads(row["final_order"]),
                "won_markets": json.loads(row["won_markets"] or "[]"),
            }

    def get_pending_bets(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT bet_id, race_id, runner_num, runner_name, place_odd, stake FROM bets WHERE result = 'PENDING' ORDER BY bet_id ASC"
            ).fetchall()
            return [dict(r) for r in rows]
