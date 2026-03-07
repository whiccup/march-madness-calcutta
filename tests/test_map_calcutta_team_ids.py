"""Tests for Calcutta team ID mapping script."""

from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "map_calcutta_team_ids.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("map_calcutta_team_ids", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class MapCalcuttaTeamIdsTests(unittest.TestCase):
    def test_maps_single_and_combo_rows(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            calcutta = tmp / "calcutta.csv"
            spellings = tmp / "spellings.csv"
            seeds = tmp / "seeds.csv"
            out = tmp / "out.csv"
            review = tmp / "review.csv"
            overrides = tmp / "overrides.csv"

            _write_csv(
                calcutta,
                ["year", "team_name", "winning_bid"],
                [
                    {"year": "2025", "team_name": "UConn", "winning_bid": "1000"},
                    {"year": "2025", "team_name": "TX/Xav", "winning_bid": "500"},
                ],
            )
            _write_csv(
                spellings,
                ["TeamNameSpelling", "TeamID"],
                [
                    {"TeamNameSpelling": "uconn", "TeamID": "1163"},
                    {"TeamNameSpelling": "texas", "TeamID": "1400"},
                    {"TeamNameSpelling": "xavier", "TeamID": "1462"},
                ],
            )
            _write_csv(
                seeds,
                ["Season", "Seed", "TeamID"],
                [
                    {"Season": "2025", "Seed": "X01", "TeamID": "1163"},
                    {"Season": "2025", "Seed": "X11a", "TeamID": "1400"},
                    {"Season": "2025", "Seed": "X11b", "TeamID": "1462"},
                ],
            )
            _write_csv(
                overrides,
                ["year", "team_name", "team_id_primary", "team_id_a", "team_id_b", "note"],
                [],
            )

            mapped_count, review_count = module.map_calcutta_rows(
                calcutta_csv=calcutta,
                spellings_csv=spellings,
                seeds_csv=seeds,
                output_csv=out,
                review_csv=review,
                overrides_csv=overrides,
                years={2025},
            )
            self.assertEqual(mapped_count, 2)
            self.assertEqual(review_count, 0)

            with out.open(encoding="utf-8", newline="") as fp:
                rows = list(csv.DictReader(fp))
            uconn = next(row for row in rows if row["team_name"] == "UConn")
            combo = next(row for row in rows if row["team_name"] == "TX/Xav")
            self.assertEqual(uconn["mapping_status"], "mapped_single")
            self.assertEqual(uconn["team_id_primary"], "1163")
            self.assertEqual(combo["mapping_status"], "mapped_combo")
            self.assertEqual(combo["team_id_a"], "1400")
            self.assertEqual(combo["team_id_b"], "1462")

    def test_unresolved_goes_to_review(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            calcutta = tmp / "calcutta.csv"
            spellings = tmp / "spellings.csv"
            seeds = tmp / "seeds.csv"
            out = tmp / "out.csv"
            review = tmp / "review.csv"
            overrides = tmp / "overrides.csv"

            _write_csv(
                calcutta,
                ["year", "team_name", "winning_bid"],
                [{"year": "2025", "team_name": "Unknown Team", "winning_bid": "100"}],
            )
            _write_csv(
                spellings,
                ["TeamNameSpelling", "TeamID"],
                [{"TeamNameSpelling": "uconn", "TeamID": "1163"}],
            )
            _write_csv(
                seeds,
                ["Season", "Seed", "TeamID"],
                [{"Season": "2025", "Seed": "X01", "TeamID": "1163"}],
            )
            _write_csv(
                overrides,
                ["year", "team_name", "team_id_primary", "team_id_a", "team_id_b", "note"],
                [],
            )

            mapped_count, review_count = module.map_calcutta_rows(
                calcutta_csv=calcutta,
                spellings_csv=spellings,
                seeds_csv=seeds,
                output_csv=out,
                review_csv=review,
                overrides_csv=overrides,
                years={2025},
            )
            self.assertEqual(mapped_count, 1)
            self.assertEqual(review_count, 1)

            with out.open(encoding="utf-8", newline="") as fp:
                row = next(csv.DictReader(fp))
            self.assertEqual(row["mapping_status"], "unresolved_single")

            with review.open(encoding="utf-8", newline="") as fp:
                review_row = next(csv.DictReader(fp))
            self.assertEqual(review_row["team_name"], "Unknown Team")


if __name__ == "__main__":
    unittest.main()
