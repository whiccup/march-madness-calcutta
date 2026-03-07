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

    def test_portfolio_includes_round_one_and_biggest_loser_ev(self) -> None:
        bids = [{"team": "A", "bid_amount": 10.0}]
        payout_rules = {
            "total_pot": 100.0,
            "finish_percentages": {"CHAMP": 0.07},
            "round_one_rules": {
                "total_percentage": 0.29,
                "split": "equal",
                "seed_payout_rules": {"1-3": "EXCLUDE", "4-12": "WIN", "13-16": "COVER"},
            },
            "special_percentages": {"BIGGEST_LOSER": 0.04},
        }
        finish_counts = {"A": {"CHAMP": 50}}
        special_shares = {"ROUND1": {"A": 0.2}, "BIGGEST_LOSER": {"A": 0.1}}

        report = evaluate_portfolio(
            bids=bids,
            payout_rules=payout_rules,
            finish_counts=finish_counts,
            total_runs=100,
            special_event_shares=special_shares,
        )

        # CHAMP: 0.5*7 + ROUND1: 0.2*29 + BIGGEST_LOSER: 0.1*4 = 9.7
        self.assertAlmostEqual(report["expected_payout"], 9.7, places=6)


if __name__ == "__main__":
    unittest.main()
