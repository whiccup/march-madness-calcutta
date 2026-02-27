from __future__ import annotations

from calcutta_sim.core.models import ROUND_ORDER


def evaluate_portfolio(
    bids: list[dict],
    payout_rules: dict,
    finish_counts: dict[str, dict[str, int]],
    total_runs: int,
) -> dict:
    if total_runs <= 0:
        raise ValueError("total_runs must be > 0")

    finish_percentages = payout_rules.get("finish_percentages", {})
    total_pot = float(payout_rules.get("total_pot") or 0.0)
    if total_pot <= 0.0:
        total_pot = sum(float(b["bid_amount"]) for b in bids)

    team_breakdown = []
    total_spend = 0.0
    expected_payout = 0.0

    for bid in bids:
        team = bid["team"]
        bid_amount = float(bid["bid_amount"])
        total_spend += bid_amount

        team_counts = finish_counts.get(team, {})
        team_expected = 0.0
        finish_probs = {}
        for finish in ROUND_ORDER:
            prob = team_counts.get(finish, 0) / total_runs
            finish_probs[finish] = prob
            team_expected += prob * total_pot * float(finish_percentages.get(finish, 0.0))

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
