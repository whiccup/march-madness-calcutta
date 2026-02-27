"""Plugin strategy loading tests."""

from __future__ import annotations

import unittest

from calcutta_sim.core.auction_strategy import AuctionContext, ParticipantState
from calcutta_sim.core.models import Team
from calcutta_sim.core.strategies import build_strategy
from calcutta_sim.core.validate import ValidationError


class PluginStrategyTests(unittest.TestCase):
    """Verify plugin loading and protocol checks."""

    def _ctx(self) -> AuctionContext:
        return AuctionContext(
            team=Team(team="X", seed=8, region="West", slot=10),
            team_expected_value=50.0,
            min_increment=5.0,
            participant_count=2,
            settings={},
        )

    def _state(self) -> ParticipantState:
        return ParticipantState(name="PluginUser", bankroll_total=100.0, remaining_bankroll=100.0)

    def test_load_valid_plugin(self) -> None:
        strategy = build_strategy(
            {
                "kind": "plugin",
                "path": "tests.plugin_fixtures:ConstantBidStrategy",
                "params": {"cap": 42},
            }
        )
        self.assertEqual(strategy.max_bid(self._ctx(), self._state()), 42.0)

    def test_invalid_plugin_path_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            build_strategy({"kind": "plugin", "path": "badpath", "params": {}})

    def test_plugin_without_max_bid_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            build_strategy(
                {
                    "kind": "plugin",
                    "path": "tests.plugin_fixtures:NoBidMethod",
                    "params": {},
                }
            )


if __name__ == "__main__":
    unittest.main()

