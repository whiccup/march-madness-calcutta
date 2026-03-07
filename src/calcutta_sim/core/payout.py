"""Payout rule helpers shared by simulation, portfolio, and auction EV paths."""

from __future__ import annotations

from typing import Any

from calcutta_sim.core.models import ROUND_ORDER


def _parse_seed_bucket(text: str) -> tuple[int, int]:
    start_text, end_text = text.split("-", 1)
    start = int(start_text)
    end = int(end_text)
    if start > end:
        raise ValueError(f"Invalid seed bucket range: {text}")
    return start, end


def get_seed_rule_map(payout_rules: dict[str, Any]) -> dict[int, str]:
    """Expand configured round-one seed rules into seed -> behavior mapping."""

    round_one_rules = payout_rules.get("round_one_rules", {})
    seed_rules = round_one_rules.get("seed_payout_rules", {})
    expanded: dict[int, str] = {}
    for bucket, behavior in seed_rules.items():
        start, end = _parse_seed_bucket(str(bucket))
        for seed in range(start, end + 1):
            expanded[seed] = str(behavior).upper()
    return expanded


def round_one_total_percentage(payout_rules: dict[str, Any]) -> float:
    """Return configured total pool percentage for round-one event payouts."""

    round_one_rules = payout_rules.get("round_one_rules", {})
    return float(round_one_rules.get("total_percentage", 0.0))


def biggest_loser_percentage(payout_rules: dict[str, Any]) -> float:
    """Return configured biggest-loser pool percentage."""

    special = payout_rules.get("special_percentages", {})
    return float(special.get("BIGGEST_LOSER", 0.0))


def resolve_total_pot(payout_rules: dict[str, Any], default_pot: float) -> float:
    """Use configured total pot when present, otherwise fallback."""

    total_pot = float(payout_rules.get("total_pot") or 0.0)
    if total_pot > 0:
        return total_pot
    return default_pot


def compute_team_expected_values(
    payout_rules: dict[str, Any],
    total_runs: int,
    finish_counts: dict[str, dict[str, int]],
    special_event_shares: dict[str, dict[str, float]] | None,
    total_pot: float,
) -> dict[str, float]:
    """Compute expected payout by team from finish + special event share metrics."""

    finish_percentages = payout_rules.get("finish_percentages", {})
    round_one_pct = round_one_total_percentage(payout_rules)
    biggest_loser_pct = biggest_loser_percentage(payout_rules)

    round_one_shares = (special_event_shares or {}).get("ROUND1", {})
    biggest_loser_shares = (special_event_shares or {}).get("BIGGEST_LOSER", {})

    team_names = set(finish_counts)
    team_names.update(round_one_shares)
    team_names.update(biggest_loser_shares)

    values: dict[str, float] = {}
    for team in team_names:
        counts = finish_counts.get(team, {})
        ev = 0.0
        for finish in ROUND_ORDER:
            prob = counts.get(finish, 0) / total_runs
            ev += prob * total_pot * float(finish_percentages.get(finish, 0.0))

        ev += total_pot * round_one_pct * float(round_one_shares.get(team, 0.0))
        ev += total_pot * biggest_loser_pct * float(biggest_loser_shares.get(team, 0.0))
        values[team] = ev
    return values
