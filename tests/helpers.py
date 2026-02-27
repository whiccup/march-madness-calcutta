"""Shared test fixtures for synthetic team and odds data."""

from __future__ import annotations

from calcutta_sim.core.models import Team


def build_teams() -> list[Team]:
    """Create a valid deterministic 64-team bracket fixture."""

    regions = ["East", "West", "South", "Midwest"]
    teams: list[Team] = []
    slot = 1
    for region in regions:
        for seed in range(1, 17):
            teams.append(Team(team=f"{region}-{seed}", seed=seed, region=region, slot=slot))
            slot += 1
    return teams


def build_odds(teams: list[Team]) -> dict[str, float]:
    """Create monotonically worse odds for higher seed numbers."""

    odds = {}
    for team in teams:
        # Better seeds get better championship odds.
        odds[team.team] = 5.0 + team.seed * 2.0
    return odds


def build_participants() -> list[dict]:
    """Create deterministic participant fixtures for auction tests."""

    return [
        {
            "name": "Alpha",
            "bankroll": 300.0,
            "strategy": {
                "kind": "builtin",
                "name": "ev_threshold",
                "params": {"aggressiveness": 1.0},
            },
        },
        {
            "name": "Beta",
            "bankroll": 300.0,
            "strategy": {
                "kind": "builtin",
                "name": "flat_discount",
                "params": {"discount": 1.0},
            },
        },
    ]
