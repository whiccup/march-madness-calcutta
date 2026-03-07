"""Expected payout and profit calculations for owned Calcutta teams."""

from __future__ import annotations

from calcutta_sim.core.models import ROUND_ORDER
from calcutta_sim.core.payout import (
    biggest_loser_percentage,
    compute_team_expected_values,
    resolve_total_pot,
    round_one_total_percentage,
)
from calcutta_sim.core.validate import ValidationError, validate_payout_rules


def evaluate_portfolio(
    bids: list[dict],
    payout_rules: dict,
    finish_counts: dict[str, dict[str, int]],
    total_runs: int,
    special_event_shares: dict[str, dict[str, float]] | None = None,
) -> dict:
    """Compute team-level and total expected payout/profit from simulation output."""

    if total_runs <= 0:
        raise ValueError("total_runs must be > 0")

    validate_payout_rules(payout_rules)
    total_pot = resolve_total_pot(payout_rules, sum(float(b["bid_amount"]) for b in bids))
    needs_specials = round_one_total_percentage(payout_rules) > 0 or biggest_loser_percentage(
        payout_rules
    ) > 0
    if needs_specials and not special_event_shares:
        raise ValidationError(
            "Simulation summary is missing special_event_shares required by payout rules"
        )

    team_expected_values = compute_team_expected_values(
        payout_rules=payout_rules,
        total_runs=total_runs,
        finish_counts=finish_counts,
        special_event_shares=special_event_shares,
        total_pot=total_pot,
    )

    team_breakdown = []
    total_spend = 0.0
    expected_payout = 0.0

    for bid in bids:
        team = bid["team"]
        bid_amount = float(bid["bid_amount"])
        total_spend += bid_amount

        team_expected = team_expected_values.get(team, 0.0)
        team_counts = finish_counts.get(team, {})
        finish_probs = {
            finish: team_counts.get(finish, 0) / total_runs for finish in ROUND_ORDER
        }

        expected_payout += team_expected
        team_breakdown.append(
            {
                "team": team,
                "bid_amount": bid_amount,
                "expected_payout": team_expected,
                "expected_profit": team_expected - bid_amount,
                "finish_probabilities": finish_probs,
            }
        )

    return {
        "total_pot": total_pot,
        "total_spend": total_spend,
        "expected_payout": expected_payout,
        "expected_profit": expected_payout - total_spend,
        "team_breakdown": sorted(team_breakdown, key=lambda x: x["expected_profit"], reverse=True),
    }
