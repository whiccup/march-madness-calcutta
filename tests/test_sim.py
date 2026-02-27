from __future__ import annotations

import unittest

from calcutta_sim.core.odds import odds_to_strengths
from calcutta_sim.core.sim import run_simulations
from tests.helpers import build_odds, build_teams


class SimTests(unittest.TestCase):
    def test_simulation_outputs_valid_probability_mass(self) -> None:
        teams = build_teams()
        odds = build_odds(teams)
        strengths = odds_to_strengths(odds)

        summary, _ = run_simulations(teams=teams, strengths=strengths, runs=500, seed=42)

        champ_total = sum(summary["champion_probabilities"].values())
        self.assertLess(abs(champ_total - 1.0), 1e-9)

    def test_simulation_seed_is_reproducible(self) -> None:
        teams = build_teams()
        strengths = odds_to_strengths(build_odds(teams))

        s1, _ = run_simulations(teams=teams, strengths=strengths, runs=200, seed=7)
        s2, _ = run_simulations(teams=teams, strengths=strengths, runs=200, seed=7)
        self.assertEqual(s1, s2)


if __name__ == "__main__":
    unittest.main()
