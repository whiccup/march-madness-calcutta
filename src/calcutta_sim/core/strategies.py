"""Built-in and plugin-backed auction strategies."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from calcutta_sim.core.auction_strategy import AuctionContext, AuctionStrategy, ParticipantState
from calcutta_sim.core.validate import ValidationError


@dataclass
class EvThresholdStrategy:
    """Bid up to EV times an aggressiveness multiplier."""

    aggressiveness: float = 1.0

    def max_bid(self, context: AuctionContext, state: ParticipantState) -> float:
        return max(0.0, context.team_expected_value * self.aggressiveness)


@dataclass
class FlatDiscountStrategy:
    """Bid up to EV minus a fixed discount amount."""

    discount: float = 0.0

    def max_bid(self, context: AuctionContext, state: ParticipantState) -> float:
        return max(0.0, context.team_expected_value - self.discount)


@dataclass
class SeedBiasStrategy:
    """Adjust EV by seed preference where lower seeds can be favored."""

    base_aggressiveness: float = 1.0
    seed_weight: float = 0.0

    def max_bid(self, context: AuctionContext, state: ParticipantState) -> float:
        # Positive seed_weight favors better seeds (smaller numeric seed).
        adjustment = 1.0 + self.seed_weight * ((17 - context.team.seed) / 16.0)
        return max(0.0, context.team_expected_value * self.base_aggressiveness * adjustment)


BUILTIN_STRATEGIES: dict[str, type] = {
    "ev_threshold": EvThresholdStrategy,
    "flat_discount": FlatDiscountStrategy,
    "seed_bias": SeedBiasStrategy,
}


def _load_plugin_class(path: str) -> type:
    if ":" not in path:
        raise ValidationError(
            f"Invalid plugin path '{path}'. Expected format module.path:ClassName"
        )
    module_name, class_name = path.split(":", 1)
    if not module_name or not class_name:
        raise ValidationError(
            f"Invalid plugin path '{path}'. Expected format module.path:ClassName"
        )
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - error text asserted via CLI tests
        raise ValidationError(f"Failed to import strategy module '{module_name}': {exc}") from exc

    if not hasattr(module, class_name):
        raise ValidationError(f"Strategy class '{class_name}' not found in module '{module_name}'")
    strategy_cls = getattr(module, class_name)
    if not isinstance(strategy_cls, type):
        raise ValidationError(f"Strategy target '{path}' is not a class")
    return strategy_cls


def build_strategy(spec: dict[str, Any]) -> AuctionStrategy:
    """Instantiate a strategy from validated spec."""

    kind = str(spec.get("kind", "builtin"))
    params = spec.get("params") or {}
    if not isinstance(params, dict):
        raise ValidationError("Strategy params must be an object")

    if kind == "builtin":
        name = str(spec.get("name", ""))
        if name not in BUILTIN_STRATEGIES:
            supported = ", ".join(sorted(BUILTIN_STRATEGIES))
            raise ValidationError(f"Unknown builtin strategy '{name}'. Choose from: {supported}")
        try:
            return BUILTIN_STRATEGIES[name](**params)
        except TypeError as exc:
            raise ValidationError(f"Invalid params for builtin strategy '{name}': {exc}") from exc

    if kind == "plugin":
        path = str(spec.get("path", ""))
        strategy_cls = _load_plugin_class(path)
        try:
            strategy = strategy_cls(params)
        except TypeError:
            try:
                strategy = strategy_cls(**params)
            except TypeError as exc:
                raise ValidationError(
                    f"Could not construct plugin strategy '{path}' with provided params: {exc}"
                ) from exc

        if not hasattr(strategy, "max_bid") or not callable(strategy.max_bid):
            raise ValidationError(f"Plugin strategy '{path}' must implement callable max_bid(...)")
        return strategy

    raise ValidationError("Strategy kind must be either 'builtin' or 'plugin'")

