#!/usr/bin/env python3
"""Generate men team-year NCAA tournament stage flags from Kaggle dataset files."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


OUTPUT_COLUMNS = [
    "season",
    "team_id",
    "team_name",
    "reached_playin",
    "won_playin",
    "reached_r64",
    "reached_r32",
    "reached_s16",
    "reached_e8",
    "reached_f4",
    "reached_f2",
    "won_championship",
]


def _is_playin_seed(seed: str) -> bool:
    seed = str(seed).strip()
    return len(seed) == 4 and seed[-1].lower() in {"a", "b"}


def _load_teams(path: Path) -> dict[int, str]:
    teams: dict[int, str] = {}
    with path.open(encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            teams[int(row["TeamID"])] = row["TeamName"]
    return teams


def _load_seeds(path: Path) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    with path.open(encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            rows.append(
                {
                    "season": int(row["Season"]),
                    "team_id": int(row["TeamID"]),
                    "seed": row["Seed"],
                }
            )
    return rows


def _load_wins(path: Path) -> dict[tuple[int, int], int]:
    wins: dict[tuple[int, int], int] = defaultdict(int)
    with path.open(encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            season = int(row["Season"])
            winner = int(row["WTeamID"])
            wins[(season, winner)] += 1
    return dict(wins)


def _stage_flags_for_team(is_playin: bool, total_wins: int) -> dict[str, int]:
    if is_playin:
        reached_playin = 1
        won_playin = 1 if total_wins >= 1 else 0
        reached_r64 = won_playin
        main_wins = max(total_wins - 1, 0)
    else:
        reached_playin = 0
        won_playin = 0
        reached_r64 = 1
        main_wins = total_wins

    return {
        "reached_playin": reached_playin,
        "won_playin": won_playin,
        "reached_r64": reached_r64,
        "reached_r32": 1 if main_wins >= 1 else 0,
        "reached_s16": 1 if main_wins >= 2 else 0,
        "reached_e8": 1 if main_wins >= 3 else 0,
        "reached_f4": 1 if main_wins >= 4 else 0,
        "reached_f2": 1 if main_wins >= 5 else 0,
        "won_championship": 1 if main_wins >= 6 else 0,
    }


def generate_team_year_stage_rows(
    teams_by_id: dict[int, str],
    seeds: list[dict[str, int | str]],
    wins_by_team: dict[tuple[int, int], int],
    season_filter: int | None = None,
) -> list[dict[str, int | str]]:
    """Build team-year stage rows for all seeded tournament teams."""

    rows: list[dict[str, int | str]] = []
    for seed_row in seeds:
        season = int(seed_row["season"])
        if season_filter is not None and season != season_filter:
            continue
        team_id = int(seed_row["team_id"])
        seed = str(seed_row["seed"])
        total_wins = wins_by_team.get((season, team_id), 0)
        flags = _stage_flags_for_team(_is_playin_seed(seed), total_wins)

        row: dict[str, int | str] = {
            "season": season,
            "team_id": team_id,
            "team_name": teams_by_id.get(team_id, ""),
        }
        row.update(flags)
        rows.append(row)

    rows.sort(key=lambda r: (int(r["season"]), int(r["team_id"])))
    return rows


def _write_csv(path: Path, rows: list[dict[str, int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--teams",
        type=Path,
        default=Path("data/march-machine-learning-mania-2026/MTeams.csv"),
    )
    parser.add_argument(
        "--seeds",
        type=Path,
        default=Path("data/march-machine-learning-mania-2026/MNCAATourneySeeds.csv"),
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("data/march-machine-learning-mania-2026/MNCAATourneyCompactResults.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/march-machine-learning-mania-2026/m_team_year_stages.csv"),
    )
    parser.add_argument("--season", type=int, default=None)
    args = parser.parse_args()

    teams_by_id = _load_teams(args.teams)
    seeds = _load_seeds(args.seeds)
    wins = _load_wins(args.results)
    rows = generate_team_year_stage_rows(
        teams_by_id=teams_by_id,
        seeds=seeds,
        wins_by_team=wins,
        season_filter=args.season,
    )
    _write_csv(args.output, rows)
    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
