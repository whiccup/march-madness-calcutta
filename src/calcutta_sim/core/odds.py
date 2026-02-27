from __future__ import annotations


def _to_implied_probability(value: float) -> float:
    # Values <=1 are treated as probability; >1 as decimal odds.
    if value <= 1.0:
        return value
    return 1.0 / value


def odds_to_strengths(raw_odds: dict[str, float]) -> dict[str, float]:
    implied = {team: _to_implied_probability(value) for team, value in raw_odds.items()}
    total = sum(implied.values())
    if total <= 0:
        raise ValueError("Odds imply zero total probability")

    normalized = {team: prob / total for team, prob in implied.items()}
    # Damp extremes slightly while preserving ordering.
    return {team: prob ** (1.0 / 2.0) for team, prob in normalized.items()}


def win_probability(team_a: str, team_b: str, strengths: dict[str, float]) -> float:
    a = strengths[team_a]
    b = strengths[team_b]
    return a / (a + b)
