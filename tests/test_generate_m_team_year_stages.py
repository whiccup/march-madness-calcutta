"""Tests for men team-year tournament stage generation script."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_m_team_year_stages.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_m_team_year_stages", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GenerateMTeamYearStagesTests(unittest.TestCase):
    def test_non_playin_stage_progression(self) -> None:
        module = _load_module()
        flags = module._stage_flags_for_team(is_playin=False, total_wins=3)
        self.assertEqual(flags["reached_playin"], 0)
        self.assertEqual(flags["reached_r64"], 1)
        self.assertEqual(flags["reached_r32"], 1)
        self.assertEqual(flags["reached_s16"], 1)
        self.assertEqual(flags["reached_e8"], 1)
        self.assertEqual(flags["reached_f4"], 0)

    def test_playin_loser_does_not_reach_r64(self) -> None:
        module = _load_module()
        flags = module._stage_flags_for_team(is_playin=True, total_wins=0)
        self.assertEqual(flags["reached_playin"], 1)
        self.assertEqual(flags["won_playin"], 0)
        self.assertEqual(flags["reached_r64"], 0)
        self.assertEqual(flags["reached_r32"], 0)

    def test_playin_champion_has_title_flag(self) -> None:
        module = _load_module()
        flags = module._stage_flags_for_team(is_playin=True, total_wins=7)
        self.assertEqual(flags["won_playin"], 1)
        self.assertEqual(flags["won_championship"], 1)
        self.assertEqual(flags["reached_f2"], 1)

    def test_row_generation_filters_by_season(self) -> None:
        module = _load_module()
        teams = {1001: "A", 1002: "B"}
        seeds = [
            {"season": 2024, "team_id": 1001, "seed": "W01"},
            {"season": 2025, "team_id": 1002, "seed": "W16a"},
        ]
        wins = {(2024, 1001): 6, (2025, 1002): 1}
        rows = module.generate_team_year_stage_rows(teams, seeds, wins, season_filter=2025)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["season"], 2025)
        self.assertEqual(row["team_name"], "B")
        self.assertEqual(row["won_playin"], 1)


if __name__ == "__main__":
    unittest.main()
