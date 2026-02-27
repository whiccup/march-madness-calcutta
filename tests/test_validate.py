"""Validation-focused unit tests."""

from __future__ import annotations

import unittest

from calcutta_sim.core.validate import (
    ValidationError,
    validate_auction_participants,
    validate_odds,
    validate_teams,
)
from tests.helpers import build_odds, build_teams


class ValidateTests(unittest.TestCase):
    """Covers team and odds input validation failure/success paths."""

    def test_validate_teams_accepts_valid_shape(self) -> None:
        """Accept a complete well-formed 64-team structure."""

        teams = build_teams()
        validate_teams(teams)

    def test_validate_teams_rejects_missing_team(self) -> None:
        """Reject incomplete team lists."""

        teams = build_teams()[:-1]
        with self.assertRaises(ValidationError):
            validate_teams(teams)

    def test_validate_odds_rejects_missing_team_odds(self) -> None:
        """Reject odds inputs that do not cover every team."""

        teams = build_teams()
        odds = build_odds(teams)
        odds.pop(teams[0].team)
        with self.assertRaises(ValidationError):
            validate_odds(teams, odds)

    def test_validate_auction_participants_rejects_duplicate_names(self) -> None:
        """Reject participant configs with duplicate bidder names."""

        participants = [
            {
                "name": "A",
                "bankroll": 100,
                "strategy": {"kind": "builtin", "name": "ev_threshold", "params": {}},
            },
            {
                "name": "A",
                "bankroll": 120,
                "strategy": {"kind": "builtin", "name": "flat_discount", "params": {}},
            },
        ]
        with self.assertRaises(ValidationError):
            validate_auction_participants(participants)

    def test_validate_auction_participants_allows_unlimited_without_bankroll(self) -> None:
        """Allow missing bankroll when unlimited bankroll is explicitly enabled."""

        participants = [
            {
                "name": "A",
                "unlimited_bankroll": True,
                "strategy": {"kind": "builtin", "name": "ev_threshold", "params": {}},
            }
        ]
        validate_auction_participants(participants)

    def test_validate_auction_participants_rejects_negative_soft_cap_decay(self) -> None:
        """Reject negative per-participant soft cap decay values."""

        participants = [
            {
                "name": "A",
                "bankroll": 100,
                "soft_cap_decay": -0.2,
                "strategy": {"kind": "builtin", "name": "ev_threshold", "params": {}},
            }
        ]
        with self.assertRaises(ValidationError):
            validate_auction_participants(participants)


if __name__ == "__main__":
    unittest.main()
