"""Plugin fixtures used by auction strategy loading tests."""

from __future__ import annotations

from calcutta_sim.core.auction_strategy import AuctionContext, ParticipantState


class ConstantBidStrategy:
    """Simple plugin strategy that returns a configured fixed cap."""

    def __init__(self, params: dict):
        self.cap = float(params.get("cap", 10.0))

    def max_bid(self, context: AuctionContext, state: ParticipantState) -> float:
        return self.cap


class NoBidMethod:
    """Invalid plugin class without required max_bid callable."""

    def __init__(self, params: dict):
        self.params = params

