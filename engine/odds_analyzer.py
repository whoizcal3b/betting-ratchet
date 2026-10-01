from typing import List, Dict, Any, Optional

class OddsAnalyzer:
    def __init__(self, min_odds: float = 2.80):
        self.min_odds = float(min_odds)

    def analyze_race(self, runners: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Applies Odd Algo rules to the 4-runner field:
        - 0 runners >= 2.80: SKIP
        - 1 runner >= 2.80: BET that runner
        - Multiple runners >= 2.80: BET the runner with highest Place odd, journal all candidates.
        """
        qualifying = []
        for r in runners:
            try:
                p_odd = float(r["place_odd"])
            except (ValueError, TypeError):
                p_odd = 0.0

            if p_odd >= self.min_odds:
                qualifying.append({
                    "runner_num": r["runner_num"],
                    "runner_name": r["runner_name"],
                    "win_odd": float(r["win_odd"]),
                    "place_odd": p_odd,
                    "element": r.get("place_element")
                })

        num_cand = len(qualifying)

        if num_cand == 0:
            return {
                "decision": "SKIP",
                "reason": f"No runners with Place odds >= {self.min_odds:.2f}",
                "target_runner": None,
                "candidates": []
            }

        # Sort descending by place_odd
        qualifying.sort(key=lambda x: x["place_odd"], reverse=True)
        chosen_runner = qualifying[0]

        reason = "Single qualifying runner" if num_cand == 1 else f"Selected highest odd among {num_cand} candidates >= {self.min_odds:.2f}"

        return {
            "decision": "BET",
            "reason": reason,
            "target_runner": chosen_runner,
            "candidates": qualifying
        }
