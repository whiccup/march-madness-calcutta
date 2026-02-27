"""Built-in strategy and loader tests."""

from __future__ import annotations

import unittest

from calcutta_sim.core.auction_strategy import AuctionContext, ParticipantState
from calcutta_sim.core.models import Team
from calcutta_sim.core.strategies import build_strategy
from calcutta_sim.core.validate import ValidationError


class StrategyTests(unittest.TestCase):
    """Validate built-in strategy behavior and config errors."""

    def _ctx(self) -> AuctionContext:
        return AuctionContext(
            team=Team(team="X", seed=4, region="East", slot=1),
            team_expected_value=100.0,
            min_increment=5.0,
            participant_count=2,
            settings={},
        )

    def _state(self) -> ParticipantState:
        return ParticipantState(name="A", bankroll_total=200.0, remaining_bankroll=200.0)

    def test_ev_threshold(self) -> None:
        strategy = build_strategy(
            {"kind": "builtin", "name": "ev_threshold", "params": {"aggressiveness": 0.9}}
        )
        self.assertAlmostEqual(strategy.max_bid(self._ctx(), self._state()), 90.0, places=6)

    def test_flat_discount(self) -> None:
        strategy = build_strategy(
            {"kind": "builtin", "name": "flat_discount", "params": {"discount": 15.0}}
        )
        self.assertAlmostEqual(strategy.max_bid(self._ctx(), self._state()), 85.0, places=6)

    def test_seed_bias(self) -> None:
        strategy = build_strategy(
            {
                "kind": "builtin",
                "name": "seed_bias",
                "params": {"base_aggressiveness": 1.0, "seed_weight": 0.2},
            }
        )
        self.assertGreater(strategy.max_bid(self._ctx(), self._state()), 100.0)

    def test_unknown_builtin_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            build_strategy({"kind": "builtin", "name": "does_not_exist", "params": {}})


if __name__ == "__main__":
    unittest.main()

