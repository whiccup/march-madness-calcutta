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
