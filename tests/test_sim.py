"""Simulation engine unit tests."""

from __future__ import annotations

import unittest

from calcutta_sim.core.odds import odds_to_strengths
from calcutta_sim.core.sim import run_simulations
from tests.helpers import build_odds, build_teams


class SimTests(unittest.TestCase):
    """Covers probability mass and deterministic seeding behavior."""

    def test_simulation_outputs_valid_probability_mass(self) -> None:
        """Champion probabilities should sum to one across all teams."""

        teams = build_teams()
        odds = build_odds(teams)
        strengths = odds_to_strengths(odds)

        summary, _ = run_simulations(teams=teams, strengths=strengths, runs=500, seed=42)

        champ_total = sum(summary["champion_probabilities"].values())
        self.assertLess(abs(champ_total - 1.0), 1e-9)

    def test_simulation_seed_is_reproducible(self) -> None:
        """Equal seeds and inputs should produce identical summaries."""

        teams = build_teams()
        strengths = odds_to_strengths(build_odds(teams))

        s1, _ = run_simulations(teams=teams, strengths=strengths, runs=200, seed=7)
        s2, _ = run_simulations(teams=teams, strengths=strengths, runs=200, seed=7)
        self.assertEqual(s1, s2)

    def test_simulation_emits_special_event_shares_when_configured(self) -> None:
        teams = build_teams()
        strengths = odds_to_strengths(build_odds(teams))
        cover_probs = {team.team: 0.5 for team in teams}
        payout_rules = {
            "finish_percentages": {"CHAMP": 0.07},
            "round_one_rules": {
                "total_percentage": 0.29,
                "split": "equal",
                "seed_payout_rules": {"1-3": "EXCLUDE", "4-12": "WIN", "13-16": "COVER"},
            },
            "special_percentages": {"BIGGEST_LOSER": 0.04},
        }

        summary, _ = run_simulations(
            teams=teams,
            strengths=strengths,
            runs=100,
            seed=9,
            payout_rules=payout_rules,
            r64_cover_probabilities=cover_probs,
        )
        self.assertIn("special_event_shares", summary)
        self.assertIn("ROUND1", summary["special_event_shares"])
        self.assertIn("BIGGEST_LOSER", summary["special_event_shares"])


if __name__ == "__main__":
    unittest.main()
