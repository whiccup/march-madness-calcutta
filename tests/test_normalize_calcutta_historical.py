"""Tests for historical Calcutta workbook normalization."""

from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "normalize_calcutta_historical.py"
SOURCE_XLSX = REPO_ROOT / "data" / "calcutta-historical" / "Calcutta.xlsx"


def _load_module():
    spec = importlib.util.spec_from_file_location("normalize_calcutta_historical", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_output_rows(module) -> list[dict[str, str]]:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "normalized.csv"
        row_count = module.convert_xlsx_to_csv(SOURCE_XLSX, out_path)
        assert row_count == 128
        with out_path.open(encoding="utf-8", newline="") as fp:
            return list(csv.DictReader(fp))


def _load_order_rows(module) -> list[dict[str, str]]:
    with tempfile.TemporaryDirectory() as tmpdir:
        normalized_path = Path(tmpdir) / "normalized.csv"
        order_path = Path(tmpdir) / "order.csv"
        normalized_count, order_count = module.convert_xlsx_to_csvs(
            SOURCE_XLSX, normalized_path, order_path
        )
        assert normalized_count == 128
        assert order_count == 128
        with order_path.open(encoding="utf-8", newline="") as fp:
            return list(csv.DictReader(fp))


class NormalizeCalcuttaHistoricalTests(unittest.TestCase):
    def test_convert_expected_row_counts_by_year(self) -> None:
        module = _load_module()
        rows = _load_output_rows(module)
        by_year = {}
        for row in rows:
            by_year[row["year"]] = by_year.get(row["year"], 0) + 1
        self.assertEqual(len(rows), 128)
        self.assertEqual(by_year, {"2024": 64, "2025": 64})

    def test_parse_2025_grid_row_has_unknown_owner_and_region(self) -> None:
        module = _load_module()
        rows = _load_output_rows(module)
        sample = next(
            row
            for row in rows
            if row["year"] == "2025" and row["region"] == "Midwest" and row["seed"] == "8"
        )
        self.assertEqual(sample["team_name"], "Gonzaga")
        self.assertEqual(sample["winning_bid"], "5800")
        self.assertEqual(sample["owner_name"], "UNKNOWN")
        self.assertEqual(sample["source_section"], "auction_grid_2025")

    def test_parse_2024_row_and_playin_split(self) -> None:
        module = _load_module()
        rows = _load_output_rows(module)

        playin_sample = next(
            row for row in rows if row["year"] == "2024" and row["team_name"] == "Howard / Wagner"
        )
        self.assertEqual(playin_sample["playin_flag"], "Y")
        self.assertEqual(playin_sample["playin_team_a"], "Howard")
        self.assertEqual(playin_sample["playin_team_b"], "Wagner")
        self.assertEqual(playin_sample["owner_name"], "Kulhman + Girardin")
        self.assertEqual(playin_sample["notes"], "Howard / Wagner + 22.5")
        self.assertEqual(playin_sample["source_section"], "results_table_2024")

    def test_order_csv_uses_table_ordering(self) -> None:
        module = _load_module()
        order_rows = _load_order_rows(module)
        by_year: dict[str, list[dict[str, str]]] = {"2025": [], "2024": []}
        for row in order_rows:
            by_year[row["year"]].append(row)

        self.assertEqual(len(by_year["2025"]), 64)
        self.assertEqual(len(by_year["2024"]), 64)

        first_2025 = by_year["2025"][0]
        fourth_2025 = by_year["2025"][3]
        self.assertEqual(first_2025["auction_order"], "1")
        self.assertEqual(first_2025["team_name"], "Gonzaga")
        self.assertEqual(first_2025["region"], "Midwest")
        self.assertEqual(fourth_2025["team_name"], "Mississippi St")
        self.assertEqual(fourth_2025["auction_order"], "4")

        first_2024 = by_year["2024"][0]
        self.assertEqual(first_2024["auction_order"], "1")
        self.assertEqual(first_2024["team_name"], "Mississippi State")
