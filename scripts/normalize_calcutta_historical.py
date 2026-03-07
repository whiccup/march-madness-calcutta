#!/usr/bin/env python3
"""Normalize historical Calcutta workbook data into a single CSV table."""

from __future__ import annotations

import argparse
import csv
import re
import zipfile
from pathlib import Path
from typing import Dict
from xml.etree import ElementTree as ET

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"a": NS_MAIN, "r": NS_REL}

OUTPUT_COLUMNS = [
    "year",
    "region",
    "seed",
    "team_name",
    "winning_bid",
    "owner_name",
    "notes",
    "team_still_alive",
    "cashed_1st_round",
    "payout_round1_bonus",
    "made_sweet_sixteen",
    "made_elite_eight",
    "made_final_four",
    "made_final_game",
    "champs",
    "biggest_loser",
    "total",
    "profit_loss",
    "roi",
    "playin_flag",
    "playin_team_a",
    "playin_team_b",
    "source_section",
    "source_row",
]

ORDER_COLUMNS = [
    "year",
    "auction_order",
    "region",
    "seed",
    "team_name",
    "winning_bid",
    "owner_name",
    "playin_flag",
    "playin_team_a",
    "playin_team_b",
    "source_section",
    "source_row",
]


def _clean_text(value: str) -> str:
    return " ".join((value or "").strip().split())


def _format_number(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    try:
        num = float(text)
    except ValueError:
        return text
    if num.is_integer():
        return str(int(num))
    return str(num)


def _parse_playin(team_name: str) -> tuple[str, str, str]:
    team = _clean_text(team_name)
    if "/" not in team:
        return "N", "", ""
    parts = [part.strip() for part in re.split(r"\s*/\s*", team) if part.strip()]
    if len(parts) < 2:
        return "N", "", ""
    team_a = parts[0]
    team_b = " / ".join(parts[1:])
    return "Y", team_a, team_b


def _resolve_sheet_path(zf: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    first_sheet = workbook.find("a:sheets", NS)[0]
    rel_id = first_sheet.attrib[f"{{{NS_REL}}}id"]
    target = rid_to_target[rel_id]
    return target if target.startswith("xl/") else f"xl/{target}"


def _load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for si in root.findall("a:si", NS):
        text = "".join(t.text or "" for t in si.findall(".//a:t", NS))
        values.append(text)
    return values


def _cell_col(ref: str) -> str:
    letters = []
    for ch in ref:
        if ch.isalpha():
            letters.append(ch)
        else:
            break
    return "".join(letters)


def _load_sheet_cells(xlsx_path: Path) -> Dict[int, Dict[str, str]]:
    with zipfile.ZipFile(xlsx_path) as zf:
        sheet_path = _resolve_sheet_path(zf)
        shared_strings = _load_shared_strings(zf)
        sheet = ET.fromstring(zf.read(sheet_path))

    rows: Dict[int, Dict[str, str]] = {}
    for row in sheet.findall(".//a:sheetData/a:row", NS):
        row_num = int(row.attrib["r"])
        row_cells: Dict[str, str] = {}
        for cell in row.findall("a:c", NS):
            ref = cell.attrib.get("r", "")
            col = _cell_col(ref)
            if not col:
                continue
            value_node = cell.find("a:v", NS)
            if value_node is None or value_node.text is None:
                continue
            value = value_node.text
            if cell.attrib.get("t") == "s":
                try:
                    value = shared_strings[int(value)]
                except (IndexError, ValueError):
                    pass
            row_cells[col] = value
        if row_cells:
            rows[row_num] = row_cells
    return rows


def _blank_row() -> dict[str, str]:
    return {key: "" for key in OUTPUT_COLUMNS}


def _parse_2025_grid(rows: Dict[int, Dict[str, str]]) -> list[dict[str, str]]:
    region_groups = [
        {"seed_col": "C", "team_col": "D", "price_col": "E", "region_col": "D"},
        {"seed_col": "G", "team_col": "H", "price_col": "I", "region_col": "H"},
        {"seed_col": "J", "team_col": "K", "price_col": "L", "region_col": "K"},
        {"seed_col": "M", "team_col": "N", "price_col": "O", "region_col": "N"},
    ]
    output: list[dict[str, str]] = []

    for group in region_groups:
        header_row = rows.get(1, {})
        region_name = _clean_text(header_row.get(group["region_col"], ""))
        for row_num in range(3, 20):
            row = rows.get(row_num, {})
            seed = _format_number(row.get(group["seed_col"], ""))
            team_name = _clean_text(row.get(group["team_col"], ""))
            winning_bid = _format_number(row.get(group["price_col"], ""))
            if not seed or not team_name or not winning_bid:
                continue
            playin_flag, playin_team_a, playin_team_b = _parse_playin(team_name)
            out_row = _blank_row()
            out_row.update(
                {
                    "year": "2025",
                    "region": region_name,
                    "seed": seed,
                    "team_name": team_name,
                    "winning_bid": winning_bid,
                    "owner_name": "UNKNOWN",
                    "playin_flag": playin_flag,
                    "playin_team_a": playin_team_a,
                    "playin_team_b": playin_team_b,
                    "source_section": "auction_grid_2025",
                    "source_row": str(row_num),
                }
            )
            output.append(out_row)
    return output


def _parse_2024_results(rows: Dict[int, Dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row_num in range(24, 91):
        row = rows.get(row_num, {})
        region = _clean_text(row.get("D", ""))
        seed = _format_number(row.get("E", ""))
        team_name = _clean_text(row.get("F", ""))
        winning_bid = _format_number(row.get("G", ""))
        if not region or not seed or not team_name or not winning_bid:
            continue
        playin_flag, playin_team_a, playin_team_b = _parse_playin(team_name)
        out_row = _blank_row()
        out_row.update(
            {
                "year": "2024",
                "region": region,
                "seed": seed,
                "team_name": team_name,
                "winning_bid": winning_bid,
                "owner_name": _clean_text(row.get("H", "")),
                "notes": _clean_text(row.get("I", "")),
                "team_still_alive": _clean_text(row.get("J", "")),
                "cashed_1st_round": _format_number(row.get("K", "")),
                "payout_round1_bonus": _format_number(row.get("L", "")),
                "made_sweet_sixteen": _format_number(row.get("M", "")),
                "made_elite_eight": _format_number(row.get("N", "")),
                "made_final_four": _format_number(row.get("O", "")),
                "made_final_game": _format_number(row.get("P", "")),
                "champs": _format_number(row.get("Q", "")),
                "biggest_loser": _format_number(row.get("R", "")),
                "total": _format_number(row.get("S", "")),
                "profit_loss": _format_number(row.get("T", "")),
                "roi": _format_number(row.get("U", "")),
                "playin_flag": playin_flag,
                "playin_team_a": playin_team_a,
                "playin_team_b": playin_team_b,
                "source_section": "results_table_2024",
                "source_row": str(row_num),
            }
        )
        output.append(out_row)
    return output


def _build_order_rows(rows: Dict[int, Dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    region_groups = [
        {"seed_col": "C", "team_col": "D", "price_col": "E", "region_col": "D"},
        {"seed_col": "G", "team_col": "H", "price_col": "I", "region_col": "H"},
        {"seed_col": "J", "team_col": "K", "price_col": "L", "region_col": "K"},
        {"seed_col": "M", "team_col": "N", "price_col": "O", "region_col": "N"},
    ]

    order = 1
    header_row = rows.get(1, {})
    for row_num in range(3, 20):
        row = rows.get(row_num, {})
        for group in region_groups:
            seed = _format_number(row.get(group["seed_col"], ""))
            team_name = _clean_text(row.get(group["team_col"], ""))
            winning_bid = _format_number(row.get(group["price_col"], ""))
            if not seed or not team_name or not winning_bid:
                continue
            playin_flag, playin_team_a, playin_team_b = _parse_playin(team_name)
            output.append(
                {
                    "year": "2025",
                    "auction_order": str(order),
                    "region": _clean_text(header_row.get(group["region_col"], "")),
                    "seed": seed,
                    "team_name": team_name,
                    "winning_bid": winning_bid,
                    "owner_name": "UNKNOWN",
                    "playin_flag": playin_flag,
                    "playin_team_a": playin_team_a,
                    "playin_team_b": playin_team_b,
                    "source_section": "auction_grid_2025",
                    "source_row": str(row_num),
                }
            )
            order += 1

    fallback_order = 1
    for row_num in range(24, 91):
        row = rows.get(row_num, {})
        region = _clean_text(row.get("D", ""))
        seed = _format_number(row.get("E", ""))
        team_name = _clean_text(row.get("F", ""))
        winning_bid = _format_number(row.get("G", ""))
        if not region or not seed or not team_name or not winning_bid:
            continue
        playin_flag, playin_team_a, playin_team_b = _parse_playin(team_name)
        auction_order = _format_number(row.get("C", "")) or str(fallback_order)
        output.append(
            {
                "year": "2024",
                "auction_order": auction_order,
                "region": region,
                "seed": seed,
                "team_name": team_name,
                "winning_bid": winning_bid,
                "owner_name": _clean_text(row.get("H", "")),
                "playin_flag": playin_flag,
                "playin_team_a": playin_team_a,
                "playin_team_b": playin_team_b,
                "source_section": "results_table_2024",
                "source_row": str(row_num),
            }
        )
        fallback_order += 1

    return output


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def convert_xlsx_to_csv(input_xlsx: Path, output_csv: Path) -> int:
    rows = _load_sheet_cells(input_xlsx)
    normalized_rows = _parse_2025_grid(rows) + _parse_2024_results(rows)
    _write_csv(output_csv, OUTPUT_COLUMNS, normalized_rows)
    return len(normalized_rows)


def convert_xlsx_to_csvs(input_xlsx: Path, output_csv: Path, order_output_csv: Path) -> tuple[int, int]:
    rows = _load_sheet_cells(input_xlsx)
    normalized_rows = _parse_2025_grid(rows) + _parse_2024_results(rows)
    order_rows = _build_order_rows(rows)
    _write_csv(output_csv, OUTPUT_COLUMNS, normalized_rows)
    _write_csv(order_output_csv, ORDER_COLUMNS, order_rows)
    return len(normalized_rows), len(order_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-xlsx",
        type=Path,
        default=Path("data/calcutta-historical/Calcutta.xlsx"),
        help="Path to source .xlsx file",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/calcutta-historical/calcutta_auction_normalized.csv"),
        help="Path to destination CSV file",
    )
    parser.add_argument(
        "--order-output-csv",
        type=Path,
        default=Path("data/calcutta-historical/calcutta_auction_order.csv"),
        help="Path to destination auction-order CSV file",
    )
    args = parser.parse_args()

    row_count, order_row_count = convert_xlsx_to_csvs(
        args.input_xlsx, args.output_csv, args.order_output_csv
    )
    print(f"Wrote {row_count} rows to {args.output_csv}")
    print(f"Wrote {order_row_count} rows to {args.order_output_csv}")


if __name__ == "__main__":
    main()
