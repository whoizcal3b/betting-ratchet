from typing import Tuple, Dict, Any

class AccountLiquidatedException(Exception):
    """Raised when the account balance reaches zero and cannot place any further bets (LIVE mode only)."""
    pass

class MathEngine:
    def __init__(self, initial_balance: float = 1000.0, divisor: float = 10.0, peak_balance: float = None, mdd_trough: float = 0.0, is_paper: bool = False):
        self.divisor = float(divisor)
        self.current_balance = float(initial_balance)
        self.peak_balance = float(peak_balance) if peak_balance is not None else float(initial_balance)
        self.mdd_trough_pct = float(mdd_trough)
        self.is_paper = is_paper

    def calculate_stake(self) -> Tuple[float, bool]:
        """
        Calculates the stake according to the High-Water Mark Peak Ratchet rule.
        In PAPER mode: Never halts or goes all-in; continues staking full 1R based on peak to stress-test true MDD.
        In LIVE mode: Halts on liquidation, triggers all-in if balance < 1R.
        Returns: (stake, is_all_in)
        """
        target_stake = round(self.peak_balance / self.divisor, 2)

        # In PAPER mode: unconstrained stress-testing to find true historical MDD
        if self.is_paper:
            return target_stake, False

        # LIVE mode: strict bankroll boundaries
        if self.current_balance <= 0:
            raise AccountLiquidatedException("Account balance is 0. System liquidated.")

        # Standard 1R bet
        if self.current_balance >= target_stake:
            return target_stake, False

        # Drawdown floor: Balance is less than 1R -> Go All-In
        print(f"[!] WARNING: Balance ({self.current_balance:.2f}) < 1R Target Stake ({target_stake:.2f}). Triggering ALL-IN!")
        return round(self.current_balance, 2), True

    def get_current_drawdown_pct(self) -> float:
        """Computes current drawdown from the peak balance. Can exceed 100% in paper mode if in negative balance."""
        if self.peak_balance <= 0:
            return 0.0
        dd = (self.peak_balance - self.current_balance) / self.peak_balance * 100.0
        return max(0.0, round(dd, 2))

    def get_current_drawdown_r(self) -> float:
        """Computes current drawdown measured strictly in R-multiples."""
        one_r = self.peak_balance / self.divisor
        if one_r <= 0:
            return 0.0
        return round((self.peak_balance - self.current_balance) / one_r, 2)

    def evaluate_result(self, is_win: bool, odds: float, stake: float) -> Dict[str, Any]:
        """
        Updates account state after bet settlement.
        """
        balance_before = self.current_balance
        peak_before = self.peak_balance

        if is_win:
            pnl = round(stake * (odds - 1.0), 2)
            self.current_balance = round(self.current_balance + pnl, 2)
            result = "WIN"
        else:
            pnl = round(-stake, 2)
            if self.is_paper:
                self.current_balance = round(self.current_balance - stake, 2)
            else:
                self.current_balance = round(max(0.0, self.current_balance - stake), 2)
            result = "LOSS"

        # Check for new high-water mark peak
        is_new_peak = False
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
            is_new_peak = True

        # Calculate drawdown from peak
        drawdown_pct = self.get_current_drawdown_pct()

        # Update maximum drawdown trough
        if drawdown_pct > self.mdd_trough_pct:
            self.mdd_trough_pct = drawdown_pct

        return {
            "result": result,
            "stake": stake,
            "odds": odds,
            "pnl": pnl,
            "balance_before": balance_before,
            "peak_before": peak_before,
            "balance_after": self.current_balance,
            "peak_after": self.peak_balance,
            "is_new_peak": is_new_peak,
            "drawdown_pct": drawdown_pct,
            "mdd_trough_pct": self.mdd_trough_pct
        }
