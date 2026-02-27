"""Portfolio EV/profit calculation unit tests."""

from __future__ import annotations

import unittest

from calcutta_sim.core.portfolio import evaluate_portfolio


class PortfolioTests(unittest.TestCase):
    """Covers expected profit arithmetic consistency."""

    def test_portfolio_expected_profit_matches_formula(self) -> None:
        """Expected profit must equal expected payout minus total spend."""

        bids = [
            {"team": "A", "bid_amount": 100.0},
            {"team": "B", "bid_amount": 50.0},
        ]
        payout_rules = {
            "total_pot": 300.0,
            "finish_percentages": {"CHAMP": 0.5, "F2": 0.1},
        }
        finish_counts = {
            "A": {"CHAMP": 50, "F2": 10},
            "B": {"CHAMP": 10, "F2": 20},
        }

        report = evaluate_portfolio(
            bids=bids,
            payout_rules=payout_rules,
            finish_counts=finish_counts,
            total_runs=100,
        )

        self.assertAlmostEqual(
            report["expected_profit"], report["expected_payout"] - report["total_spend"], places=6
        )


if __name__ == "__main__":
    unittest.main()
