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

    def test_cli_simulate_auction(self) -> None:
        """Run auction simulation command and validate output payload shape."""

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

            participants = [
                {
                    "name": "A",
                    "bankroll": 300,
                    "strategy": {
                        "kind": "builtin",
                        "name": "ev_threshold",
                        "params": {"aggressiveness": 1.0},
                    },
                },
                {
                    "name": "B",
                    "bankroll": 280,
                    "strategy": {
                        "kind": "builtin",
                        "name": "flat_discount",
                        "params": {"discount": 2.0},
                    },
                },
            ]
            payout_rules = {
                "total_pot": 1200,
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
            participants_path = tmp_path / "participants.json"
            payout_path = tmp_path / "payout_rules.json"
            out_path = tmp_path / "auction.json"

            _write_json(teams_path, teams)
            _write_json(odds_path, odds)
            _write_json(participants_path, participants)
            _write_json(payout_path, payout_rules)

            env = dict(os.environ)
            env["PYTHONPATH"] = "src"

            run = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "calcutta_sim",
                    "simulate-auction",
                    "--teams",
                    str(teams_path),
                    "--odds",
                    str(odds_path),
                    "--participants",
                    str(participants_path),
                    "--payout-rules",
                    str(payout_path),
                    "--runs",
                    "200",
                    "--seed",
                    "4",
                    "--min-increment",
                    "5",
                    "--output",
                    str(out_path),
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)
            self.assertTrue(out_path.exists())

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertIn("auction", payload)
            self.assertEqual(len(payload["auction"]["winner_ledger"]), 64)
            self.assertIn("summary_by_bidder", payload["auction"])
            self.assertIn("unsold_count", payload["auction"])

            sample_bidder = next(iter(payload["auction"]["summary_by_bidder"].values()))
            self.assertIn("purchased_teams", sample_bidder)

    def test_cli_simulate_auction_invalid_plugin(self) -> None:
        """Invalid plugin path should return a non-zero exit code."""

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

            participants = [
                {
                    "name": "Broken",
                    "bankroll": 100,
                    "strategy": {"kind": "plugin", "path": "invalid", "params": {}},
                }
            ]
            payout_rules = {"total_pot": 1000, "finish_percentages": {"CHAMP": 0.5}}

            teams_path = tmp_path / "teams.json"
            odds_path = tmp_path / "odds.json"
            participants_path = tmp_path / "participants.json"
            payout_path = tmp_path / "payout_rules.json"

            _write_json(teams_path, teams)
            _write_json(odds_path, odds)
            _write_json(participants_path, participants)
            _write_json(payout_path, payout_rules)

            env = dict(os.environ)
            env["PYTHONPATH"] = "src"

            run = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "calcutta_sim",
                    "simulate-auction",
                    "--teams",
                    str(teams_path),
                    "--odds",
                    str(odds_path),
                    "--participants",
                    str(participants_path),
                    "--payout-rules",
                    str(payout_path),
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertNotEqual(run.returncode, 0)

    def test_cli_simulate_auction_unlimited_bankroll_flag(self) -> None:
        """Global unlimited-bankroll flag should allow participants without bankroll field."""

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

            participants = [
                {
                    "name": "NoCap",
                    "strategy": {
                        "kind": "builtin",
                        "name": "ev_threshold",
                        "params": {"aggressiveness": 2.0},
                    },
                }
            ]
            payout_rules = {"total_pot": 1000, "finish_percentages": {"CHAMP": 0.5, "F2": 0.2}}

            teams_path = tmp_path / "teams.json"
            odds_path = tmp_path / "odds.json"
            participants_path = tmp_path / "participants.json"
            payout_path = tmp_path / "payout_rules.json"
            out_path = tmp_path / "auction_unlimited.json"

            _write_json(teams_path, teams)
            _write_json(odds_path, odds)
            _write_json(participants_path, participants)
            _write_json(payout_path, payout_rules)

            env = dict(os.environ)
            env["PYTHONPATH"] = "src"

            run = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "calcutta_sim",
                    "simulate-auction",
                    "--teams",
                    str(teams_path),
                    "--odds",
                    str(odds_path),
                    "--participants",
                    str(participants_path),
                    "--payout-rules",
                    str(payout_path),
                    "--unlimited-bankroll",
                    "--runs",
                    "80",
                    "--output",
                    str(out_path),
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            bidder = payload["auction"]["summary_by_bidder"]["NoCap"]
            self.assertTrue(bidder["unlimited_bankroll"])
            self.assertIsNone(bidder["remaining_bankroll"])

    def test_cli_simulate_auction_soft_cap_enabled(self) -> None:
        """Soft cap mode should permit overspending beyond bankroll with low penalty."""

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

            participants = [
                {
                    "name": "SoftCapper",
                    "bankroll": 5,
                    "strategy": {
                        "kind": "builtin",
                        "name": "ev_threshold",
                        "params": {"aggressiveness": 50.0},
                    },
                }
            ]
            payout_rules = {"total_pot": 1200, "finish_percentages": {"CHAMP": 0.5, "F2": 0.2}}

            teams_path = tmp_path / "teams.json"
            odds_path = tmp_path / "odds.json"
            participants_path = tmp_path / "participants.json"
            payout_path = tmp_path / "payout_rules.json"
            out_path = tmp_path / "auction_soft.json"

            _write_json(teams_path, teams)
            _write_json(odds_path, odds)
            _write_json(participants_path, participants)
            _write_json(payout_path, payout_rules)

            env = dict(os.environ)
            env["PYTHONPATH"] = "src"

            run = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "calcutta_sim",
                    "simulate-auction",
                    "--teams",
                    str(teams_path),
                    "--odds",
                    str(odds_path),
                    "--participants",
                    str(participants_path),
                    "--payout-rules",
                    str(payout_path),
                    "--soft-cap-enabled",
                    "--soft-cap-decay",
                    "0",
                    "--runs",
                    "80",
                    "--output",
                    str(out_path),
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            bidder = payload["auction"]["summary_by_bidder"]["SoftCapper"]
            self.assertGreater(bidder["teams_won"], 1)

    def test_cli_simulate_auction_participant_soft_cap_decay(self) -> None:
        """Participant soft_cap_decay should work even without global soft-cap flag."""

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

            participants = [
                {
                    "name": "PerParticipantSoft",
                    "bankroll": 5,
                    "soft_cap_decay": 0.0,
                    "strategy": {
                        "kind": "builtin",
                        "name": "ev_threshold",
                        "params": {"aggressiveness": 50.0},
                    },
                }
            ]
            payout_rules = {"total_pot": 1200, "finish_percentages": {"CHAMP": 0.5, "F2": 0.2}}

            teams_path = tmp_path / "teams.json"
            odds_path = tmp_path / "odds.json"
            participants_path = tmp_path / "participants.json"
            payout_path = tmp_path / "payout_rules.json"
            out_path = tmp_path / "auction_per_participant_soft.json"

            _write_json(teams_path, teams)
            _write_json(odds_path, odds)
            _write_json(participants_path, participants)
            _write_json(payout_path, payout_rules)

            env = dict(os.environ)
            env["PYTHONPATH"] = "src"

            run = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "calcutta_sim",
                    "simulate-auction",
                    "--teams",
                    str(teams_path),
                    "--odds",
                    str(odds_path),
                    "--participants",
                    str(participants_path),
                    "--payout-rules",
                    str(payout_path),
                    "--runs",
                    "80",
                    "--output",
                    str(out_path),
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            bidder = payload["auction"]["summary_by_bidder"]["PerParticipantSoft"]
            self.assertGreater(bidder["teams_won"], 1)
            self.assertEqual(bidder["soft_cap_decay"], 0.0)


if __name__ == "__main__":
    unittest.main()
