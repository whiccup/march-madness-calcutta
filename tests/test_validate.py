from __future__ import annotations

import unittest

from calcutta_sim.core.validate import ValidationError, validate_odds, validate_teams
from tests.helpers import build_odds, build_teams


class ValidateTests(unittest.TestCase):
    def test_validate_teams_accepts_valid_shape(self) -> None:
        teams = build_teams()
        validate_teams(teams)

    def test_validate_teams_rejects_missing_team(self) -> None:
        teams = build_teams()[:-1]
        with self.assertRaises(ValidationError):
            validate_teams(teams)

    def test_validate_odds_rejects_missing_team_odds(self) -> None:
        teams = build_teams()
        odds = build_odds(teams)
        odds.pop(teams[0].team)
        with self.assertRaises(ValidationError):
            validate_odds(teams, odds)


if __name__ == "__main__":
    unittest.main()
