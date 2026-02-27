"""Input validation for teams, odds, payout configuration, and auctions."""

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


def validate_auction_participants(
    participants: list[dict], force_unlimited_bankroll: bool = False
) -> None:
    """Validate participant definitions and strategy shape for auction simulation."""

    if not participants:
        raise ValidationError("At least one participant is required")

    names: list[str] = []
    for idx, participant in enumerate(participants):
        if not isinstance(participant, dict):
            raise ValidationError(f"Participant index {idx} must be an object")

        name = str(participant.get("name", "")).strip()
        if not name:
            raise ValidationError(f"Participant index {idx} missing non-empty 'name'")
        names.append(name)

        unlimited_bankroll = bool(participant.get("unlimited_bankroll", False))
        if force_unlimited_bankroll:
            unlimited_bankroll = True

        bankroll = participant.get("bankroll")
        if not unlimited_bankroll:
            if bankroll is None or float(bankroll) <= 0:
                raise ValidationError(
                    f"Participant '{name}' must have bankroll > 0 unless unlimited_bankroll is true"
                )
        elif bankroll is not None and float(bankroll) <= 0:
            raise ValidationError(
                f"Participant '{name}' bankroll must be > 0 if provided with unlimited_bankroll"
            )

        participant_soft_cap_decay = participant.get("soft_cap_decay")
        if participant_soft_cap_decay is not None and float(participant_soft_cap_decay) < 0:
            raise ValidationError(f"Participant '{name}' soft_cap_decay must be >= 0")

        strategy = participant.get("strategy")
        if not isinstance(strategy, dict):
            raise ValidationError(f"Participant '{name}' must include strategy object")

        kind = strategy.get("kind")
        if kind not in {"builtin", "plugin"}:
            raise ValidationError(f"Participant '{name}' strategy.kind must be builtin or plugin")

        params = strategy.get("params", {})
        if not isinstance(params, dict):
            raise ValidationError(f"Participant '{name}' strategy.params must be an object")

        if kind == "builtin":
            strategy_name = str(strategy.get("name", "")).strip()
            if not strategy_name:
                raise ValidationError(f"Participant '{name}' builtin strategy must include 'name'")

        if kind == "plugin":
            path = str(strategy.get("path", "")).strip()
            if not path or ":" not in path:
                raise ValidationError(
                    f"Participant '{name}' plugin strategy path must be module.path:ClassName"
                )

    dup_names = [n for n, c in Counter(names).items() if c > 1]
    if dup_names:
        raise ValidationError(f"Duplicate participant names: {', '.join(sorted(dup_names))}")
