#!/usr/bin/env python3
"""Assign canonical team IDs to Calcutta rows using year + Kaggle spellings/seeds."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


DEFAULT_ALIAS_MAP = {
    "abst": "alabamastate",
    "sfpa": "stfrancispa",
    "tx": "texas",
    "xav": "xavier",
    "sdsu": "sandiegostate",
    "unc": "northcarolina",
    "uofi": "illinois",
    "stjohn": "stjohns",
    "stmary": "saintmarys",
    "utahst": "utahstate",
    "iowast": "iowastate",
    "norfolkst": "norfolkstate",
    "mississippist": "mississippistate",
    "texasam": "texasam",
    "texasaandm": "texasam",
    "mizzou": "missouri",
    "coloradost": "coloradostate",
}

OUTPUT_EXTRA_COLUMNS = [
    "team_id_primary",
    "team_id_a",
    "team_id_b",
    "mapping_status",
    "mapping_source",
]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text).lower().strip())


def _load_spellings(path: Path) -> dict[str, set[int]]:
    index: dict[str, set[int]] = {}
    with path.open(encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            key = _normalize(row["TeamNameSpelling"])
            index.setdefault(key, set()).add(int(row["TeamID"]))
    return index


def _load_seed_team_ids(path: Path) -> dict[int, set[int]]:
    by_year: dict[int, set[int]] = {}
    with path.open(encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            year = int(row["Season"])
            by_year.setdefault(year, set()).add(int(row["TeamID"]))
    return by_year


def _load_overrides(path: Path) -> dict[tuple[int, str], dict[str, str]]:
    if not path.exists():
        return {}
    overrides: dict[tuple[int, str], dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            key = (int(row["year"]), row["team_name"].strip())
            overrides[key] = row
    return overrides


def _resolve_part(
    part: str,
    year: int,
    spellings: dict[str, set[int]],
    seed_team_ids: dict[int, set[int]],
    alias_map: dict[str, str],
) -> tuple[list[int], str]:
    token = _normalize(part)
    candidates = set(spellings.get(token, set()))
    source = "spelling_exact"

    if not candidates and token in alias_map:
        candidates = set(spellings.get(alias_map[token], set()))
        source = "alias_map"

    if not candidates and token.startswith("st"):
        candidates = set(spellings.get(f"saint{token[2:]}", set()))
        source = "heuristic_st_to_saint"

    if not candidates and token.endswith("st"):
        candidates = set(spellings.get(f"{token}ate", set()))
        source = "heuristic_st_to_state"

    if candidates:
        candidates = {team_id for team_id in candidates if team_id in seed_team_ids.get(year, set())}

    return sorted(candidates), source


def _build_mapped_row(
    row: dict[str, str],
    years: set[int],
    spellings: dict[str, set[int]],
    seed_team_ids: dict[int, set[int]],
    alias_map: dict[str, str],
    overrides: dict[tuple[int, str], dict[str, str]],
) -> tuple[dict[str, str], dict[str, str] | None]:
    mapped = dict(row)
    for key in OUTPUT_EXTRA_COLUMNS:
        mapped[key] = ""

    year = int(row["year"])
    if year not in years:
        mapped["mapping_status"] = "out_of_scope"
        mapped["mapping_source"] = "year_filter"
        return mapped, None

    override = overrides.get((year, row["team_name"].strip()))
    if override is not None:
        mapped["team_id_primary"] = (override.get("team_id_primary") or "").strip()
        mapped["team_id_a"] = (override.get("team_id_a") or "").strip()
        mapped["team_id_b"] = (override.get("team_id_b") or "").strip()
        mapped["mapping_status"] = "override"
        mapped["mapping_source"] = "manual_override"
        return mapped, None

    parts = [part.strip() for part in str(row["team_name"]).split("/") if part.strip()]
    part_results = [
        _resolve_part(part, year, spellings=spellings, seed_team_ids=seed_team_ids, alias_map=alias_map)
        for part in parts
    ]
    part_candidates = [candidates for candidates, _ in part_results]
    sources = sorted({source for _, source in part_results if source})
    mapped["mapping_source"] = ",".join(sources)

    if len(parts) == 1:
        candidates = part_candidates[0]
        if len(candidates) == 1:
            mapped["team_id_primary"] = str(candidates[0])
            mapped["mapping_status"] = "mapped_single"
            return mapped, None
        if len(candidates) == 0:
            mapped["mapping_status"] = "unresolved_single"
        else:
            mapped["mapping_status"] = "ambiguous_single"
        return mapped, {
            "year": str(year),
            "team_name": row["team_name"],
            "mapping_status": mapped["mapping_status"],
            "candidate_team_ids": "|".join(str(c) for c in candidates),
        }

    # Combo row: keep dual IDs for play-in style entries.
    if len(parts) >= 1 and len(part_candidates[0]) == 1:
        mapped["team_id_a"] = str(part_candidates[0][0])
    if len(parts) >= 2 and len(part_candidates[1]) == 1:
        mapped["team_id_b"] = str(part_candidates[1][0])

    if len(parts) >= 2 and len(part_candidates[0]) == 1 and len(part_candidates[1]) == 1:
        mapped["mapping_status"] = "mapped_combo"
        return mapped, None

    mapped["mapping_status"] = "combo_partial_or_ambiguous"
    return mapped, {
        "year": str(year),
        "team_name": row["team_name"],
        "mapping_status": mapped["mapping_status"],
        "candidate_team_ids": " ; ".join("|".join(str(c) for c in candidates) for candidates in part_candidates),
    }


def map_calcutta_rows(
    calcutta_csv: Path,
    spellings_csv: Path,
    seeds_csv: Path,
    output_csv: Path,
    review_csv: Path,
    overrides_csv: Path | None = None,
    years: set[int] | None = None,
) -> tuple[int, int]:
    years = years or {2024, 2025}
    spellings = _load_spellings(spellings_csv)
    seed_team_ids = _load_seed_team_ids(seeds_csv)
    overrides = _load_overrides(overrides_csv) if overrides_csv else {}

    with calcutta_csv.open(encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        fieldnames = list(reader.fieldnames or [])
        out_fieldnames = fieldnames + [c for c in OUTPUT_EXTRA_COLUMNS if c not in fieldnames]

        mapped_rows: list[dict[str, str]] = []
        review_rows: list[dict[str, str]] = []
        for row in reader:
            mapped, review = _build_mapped_row(
                row=row,
                years=years,
                spellings=spellings,
                seed_team_ids=seed_team_ids,
                alias_map=DEFAULT_ALIAS_MAP,
                overrides=overrides,
            )
            mapped_rows.append(mapped)
            if review is not None:
                review_rows.append(review)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(mapped_rows)

    review_csv.parent.mkdir(parents=True, exist_ok=True)
    with review_csv.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=["year", "team_name", "mapping_status", "candidate_team_ids"],
        )
        writer.writeheader()
        writer.writerows(review_rows)

    return len(mapped_rows), len(review_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--calcutta-csv",
        type=Path,
        default=Path("data/calcutta-historical/calcutta_auction_normalized.csv"),
    )
    parser.add_argument(
        "--spellings-csv",
        type=Path,
        default=Path("data/march-machine-learning-mania-2026/MTeamSpellings.csv"),
    )
    parser.add_argument(
        "--seeds-csv",
        type=Path,
        default=Path("data/march-machine-learning-mania-2026/MNCAATourneySeeds.csv"),
    )
    parser.add_argument(
        "--overrides-csv",
        type=Path,
        default=Path("data/calcutta-historical/team_id_overrides.csv"),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/calcutta-historical/calcutta_with_team_ids.csv"),
    )
    parser.add_argument(
        "--review-csv",
        type=Path,
        default=Path("data/calcutta-historical/calcutta_team_id_review.csv"),
    )
    parser.add_argument(
        "--years",
        default="2024,2025",
        help="Comma-separated list of years to map (default: 2024,2025)",
    )
    args = parser.parse_args()

    years = {int(y.strip()) for y in args.years.split(",") if y.strip()}
    mapped_count, review_count = map_calcutta_rows(
        calcutta_csv=args.calcutta_csv,
        spellings_csv=args.spellings_csv,
        seeds_csv=args.seeds_csv,
        output_csv=args.output_csv,
        review_csv=args.review_csv,
        overrides_csv=args.overrides_csv,
        years=years,
    )
    print(f"Wrote {mapped_count} rows to {args.output_csv}")
    print(f"Wrote {review_count} review rows to {args.review_csv}")


if __name__ == "__main__":
    main()
