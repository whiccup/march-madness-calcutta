"""Strategy interfaces and shared state for auction simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from calcutta_sim.core.models import Team


@dataclass
class ParticipantState:
    """Mutable bidder state updated as the auction progresses."""

    name: str
    bankroll_total: float | None
    remaining_bankroll: float
    unlimited_bankroll: bool = False
    soft_cap_decay: float | None = None
    spend: float = 0.0
    teams_won: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuctionContext:
    """Read-only context passed to strategies for bid sizing decisions."""

    team: Team
    team_expected_value: float
    min_increment: float
    participant_count: int
    settings: dict[str, Any]


class AuctionStrategy(Protocol):
    """Protocol custom and built-in strategies must implement."""

    def max_bid(self, context: AuctionContext, state: ParticipantState) -> float:
        """Return maximum willing bid for the team given current state."""
