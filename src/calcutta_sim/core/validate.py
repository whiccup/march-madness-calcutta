"""Input validation for teams, odds, and payout configuration."""

from __future__ import annotations

from collections import Counter, defaultdict

from calcutta_sim.core.models import ROUND_ORDER, Team


class ValidationError(ValueError):
    """Raised when user-provided input data fails structural validation."""

    pass


def validate_teams(teams: list[Team]) -> None:
    """Validate that teams represent a complete 64-team seeded bracket."""

    if len(teams) != 64:
        raise ValidationError(f"Expected 64 teams, found {len(teams)}")

    names = [t.team for t in teams]
    dup_names = [name for name, count in Counter(names).items() if count > 1]
    if dup_names:
        raise ValidationError(f"Duplicate team names: {', '.join(sorted(dup_names))}")

    slots = [t.slot for t in teams]
    if sorted(slots) != list(range(1, 65)):
        raise ValidationError("Slots must be unique and cover 1..64")

    region_to_seeds: dict[str, list[int]] = defaultdict(list)
    for team in teams:
        if not (1 <= team.seed <= 16):
            raise ValidationError(f"Invalid seed for {team.team}: {team.seed}")
        region_to_seeds[team.region].append(team.seed)

    if len(region_to_seeds) != 4:
        raise ValidationError("Expected exactly 4 regions")

    for region, seeds in region_to_seeds.items():
        if sorted(seeds) != list(range(1, 17)):
            raise ValidationError(f"Region {region} must contain seeds 1..16 exactly once")


def validate_odds(teams: list[Team], odds: dict[str, float]) -> None:
    """Validate odds coverage and positivity against the provided team set."""

    team_set = {t.team for t in teams}
    missing = sorted(team_set - set(odds))
    if missing:
        raise ValidationError(f"Missing odds for teams: {', '.join(missing)}")

    extras = sorted(set(odds) - team_set)
    if extras:
        raise ValidationError(f"Odds contain unknown teams: {', '.join(extras)}")

    for team, value in odds.items():
        if value <= 0:
            raise ValidationError(f"Odds value must be > 0 for {team}")


def validate_payout_rules(finish_percentages: dict[str, float]) -> None:
    """Validate payout keys and ensure percentages are non-negative and bounded."""

    unknown = sorted(set(finish_percentages) - set(ROUND_ORDER))
    if unknown:
        raise ValidationError(f"Unknown payout finish keys: {', '.join(unknown)}")

    for key, value in finish_percentages.items():
        if value < 0:
            raise ValidationError(f"Negative payout percentage for {key}")

    total = sum(finish_percentages.values())
    if total > 1.000001:
        raise ValidationError("Sum of payout percentages cannot exceed 1.0")
