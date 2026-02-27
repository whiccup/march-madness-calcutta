"""Integration tests for end-to-end CLI command flows."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _write_json(path: Path, payload: object) -> None:
    """Write JSON payload to disk for test fixtures."""

    path.write_text(json.dumps(payload), encoding="utf-8")


class IntegrationCliTests(unittest.TestCase):
    """Verifies simulate + portfolio commands work together."""

    def test_cli_simulate_and_portfolio(self) -> None:
        """Run a full CLI pipeline and validate expected output artifacts."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            regions = ["East", "West", "South", "Midwest"]
            teams = []
            odds = []
            slot = 1
            for region in regions:
                for seed in range(1, 17):
                    name = f"{region}-{seed}"
                    teams.append({"team": name, "seed": seed, "region": region, "slot": slot})
                    odds.append({"team": name, "championship_odds": 5 + 2 * seed})
                    slot += 1

            bids = [
                {"team": "East-1", "bid_amount": 120},
                {"team": "West-2", "bid_amount": 80},
            ]
            payout_rules = {
                "total_pot": 1000,
                "finish_percentages": {
                    "R32": 0.02,
                    "S16": 0.04,
                    "E8": 0.08,
                    "F4": 0.12,
                    "F2": 0.24,
                    "CHAMP": 0.5,
                },
            }

            teams_path = tmp_path / "teams.json"
            odds_path = tmp_path / "odds.json"
            bids_path = tmp_path / "bids.json"
            payout_path = tmp_path / "payout_rules.json"
            out_path = tmp_path / "run.json"

            _write_json(teams_path, teams)
            _write_json(odds_path, odds)
            _write_json(bids_path, bids)
            _write_json(payout_path, payout_rules)

            env = dict(os.environ)
            env["PYTHONPATH"] = "src"

            simulate = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "calcutta_sim",
                    "simulate",
                    "--teams",
                    str(teams_path),
                    "--odds",
                    str(odds_path),
                    "--runs",
                    "200",
                    "--seed",
                    "11",
                    "--output",
                    str(out_path),
                    "--bids",
                    str(bids_path),
                    "--payout-rules",
                    str(payout_path),
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(simulate.returncode, 0, msg=simulate.stderr)
            self.assertTrue(out_path.exists())

            portfolio = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "calcutta_sim",
                    "portfolio",
                    "--bids",
                    str(bids_path),
                    "--payout-rules",
                    str(payout_path),
                    "--sim-results",
                    str(out_path),
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(portfolio.returncode, 0, msg=portfolio.stderr)
            self.assertIn("Expected profit", portfolio.stdout)


if __name__ == "__main__":
    unittest.main()
