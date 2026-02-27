"""Auction engine behavior tests."""

from __future__ import annotations

import unittest

from calcutta_sim.core.auction import simulate_auction
from tests.helpers import build_odds, build_participants, build_teams


class AuctionEngineTests(unittest.TestCase):
    """Validate auction mechanics and invariants."""

    def test_reproducible_with_seed(self) -> None:
        teams = build_teams()
        odds = build_odds(teams)
        participants = build_participants()
        payout_rules = {"total_pot": 1000.0, "finish_percentages": {"CHAMP": 0.5, "F2": 0.2}}

        a = simulate_auction(
            teams=teams,
            odds=odds,
            payout_rules=payout_rules,
            participants=participants,
            runs=300,
            seed=9,
            min_increment=5.0,
        )
        b = simulate_auction(
            teams=teams,
            odds=odds,
            payout_rules=payout_rules,
            participants=participants,
            runs=300,
            seed=9,
            min_increment=5.0,
        )

        self.assertEqual(a["winner_ledger"], b["winner_ledger"])
        self.assertEqual(a["summary_by_bidder"], b["summary_by_bidder"])

    def test_bankroll_never_negative(self) -> None:
        teams = build_teams()
        odds = build_odds(teams)
        participants = build_participants()
        payout_rules = {"total_pot": 600.0, "finish_percentages": {"CHAMP": 0.7}}

        report = simulate_auction(
            teams=teams,
            odds=odds,
            payout_rules=payout_rules,
            participants=participants,
            runs=200,
            seed=3,
            min_increment=10.0,
        )
        for bidder in report["summary_by_bidder"].values():
            self.assertGreaterEqual(bidder["remaining_bankroll"], -1e-9)
            for team in bidder["purchased_teams"]:
                self.assertIn("seed", team)
                self.assertIn("region", team)
                self.assertIn("price", team)

    def test_min_increment_applied_for_single_bidder(self) -> None:
        teams = build_teams()
        odds = build_odds(teams)
        participants = [
            {
                "name": "Solo",
                "bankroll": 100.0,
                "strategy": {
                    "kind": "builtin",
                    "name": "ev_threshold",
                    "params": {"aggressiveness": 2.0},
                },
            }
        ]
        payout_rules = {"total_pot": 800.0, "finish_percentages": {"CHAMP": 0.8}}

        report = simulate_auction(
            teams=teams,
            odds=odds,
            payout_rules=payout_rules,
            participants=participants,
            runs=150,
            seed=2,
            min_increment=7.0,
        )

        nonzero_prices = [row["price"] for row in report["winner_ledger"] if row["price"] > 0]
        self.assertTrue(nonzero_prices)
        self.assertTrue(all(abs(price - 7.0) < 1e-9 for price in nonzero_prices))

    def test_unsold_count_matches_winner_ledger(self) -> None:
        teams = build_teams()
        odds = build_odds(teams)
        participants = [
            {
                "name": "Tiny",
                "bankroll": 20.0,
                "strategy": {
                    "kind": "builtin",
                    "name": "ev_threshold",
                    "params": {"aggressiveness": 0.5},
                },
            }
        ]
        payout_rules = {"total_pot": 400.0, "finish_percentages": {"CHAMP": 0.4}}
        report = simulate_auction(
            teams=teams,
            odds=odds,
            payout_rules=payout_rules,
            participants=participants,
            runs=100,
            seed=1,
            min_increment=5.0,
        )
        ledger_unsold = [row["team"] for row in report["winner_ledger"] if row["winner"] is None]
        self.assertEqual(report["unsold_count"], len(ledger_unsold))
        self.assertEqual(report["unsold_teams"], ledger_unsold)

    def test_unlimited_bankroll_can_be_enabled_per_participant(self) -> None:
        teams = build_teams()
        odds = build_odds(teams)
        participants = [
            {
                "name": "Infinite",
                "unlimited_bankroll": True,
                "strategy": {
                    "kind": "builtin",
                    "name": "ev_threshold",
                    "params": {"aggressiveness": 200.0},
                },
            }
        ]
        payout_rules = {"total_pot": 5000.0, "finish_percentages": {"CHAMP": 0.5, "F2": 0.2}}
        report = simulate_auction(
            teams=teams,
            odds=odds,
            payout_rules=payout_rules,
            participants=participants,
            runs=100,
            seed=4,
            min_increment=5.0,
        )
        bidder = report["summary_by_bidder"]["Infinite"]
        self.assertTrue(bidder["unlimited_bankroll"])
        self.assertIsNone(bidder["remaining_bankroll"])


if __name__ == "__main__":
    unittest.main()
