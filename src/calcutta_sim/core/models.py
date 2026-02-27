"""Shared data models and parsing helpers for simulator inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ROUND_ORDER = ["R64", "R32", "S16", "E8", "F4", "F2", "CHAMP"]
ROUND_RANK = {name: idx for idx, name in enumerate(ROUND_ORDER)}


@dataclass(frozen=True)
class Team:
    """Canonical team record used by simulation and validation."""

    team: str
    seed: int
    region: str
    slot: int


@dataclass(frozen=True)
class Bid:
    """User ownership record for a team and purchased bid amount."""

    team: str
    bid_amount: float


@dataclass(frozen=True)
class PayoutRules:
    """Calcutta payout model expressed as finish percentages and total pot."""

    total_pot: float
    finish_percentages: dict[str, float]


def parse_team(raw: dict[str, Any]) -> Team:
    """Parse an untyped JSON dictionary into a ``Team``."""

    return Team(
        team=str(raw["team"]),
        seed=int(raw["seed"]),
        region=str(raw["region"]),
        slot=int(raw["slot"]),
    )


def parse_bid(raw: dict[str, Any]) -> Bid:
    """Parse an untyped JSON dictionary into a ``Bid``."""

    return Bid(team=str(raw["team"]), bid_amount=float(raw["bid_amount"]))


def parse_payout_rules(raw: dict[str, Any]) -> PayoutRules:
    """Parse an untyped JSON dictionary into ``PayoutRules``."""

    finish_percentages = {
        str(k): float(v) for k, v in raw.get("finish_percentages", {}).items()
    }
    return PayoutRules(
        total_pot=float(raw.get("total_pot", 0.0)),
        finish_percentages=finish_percentages,
    )
