"""Auction simulation engine for Calcutta bidding scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from random import Random
from typing import Any

from calcutta_sim.core.auction_strategy import AuctionContext, ParticipantState
from calcutta_sim.core.models import ROUND_ORDER, Team
from calcutta_sim.core.odds import odds_to_strengths
from calcutta_sim.core.sim import run_simulations
from calcutta_sim.core.strategies import build_strategy
from calcutta_sim.core.validate import ValidationError, validate_auction_participants, validate_payout_rules


@dataclass(frozen=True)
class AuctionResultLine:
    """Result record for one team's auction event."""

    team: str
    winner: str | None
    price: float
    runner_up: str | None


def _team_expected_values(
    finish_counts: dict[str, dict[str, int]],
    total_runs: int,
    payout_rules: dict[str, Any],
    default_pot: float,
) -> tuple[dict[str, float], float]:
    finish_percentages = payout_rules.get("finish_percentages", {})
    validate_payout_rules(finish_percentages)

    total_pot = float(payout_rules.get("total_pot") or 0.0)
    if total_pot <= 0:
        total_pot = default_pot

    values: dict[str, float] = {}
    for team, counts in finish_counts.items():
        ev = 0.0
        for finish in ROUND_ORDER:
            prob = counts.get(finish, 0) / total_runs
            ev += prob * total_pot * float(finish_percentages.get(finish, 0.0))
        values[team] = ev
    return values, total_pot


def _price_and_winners(
    candidate_caps: list[tuple[str, float]], min_increment: float, rng: Random
) -> tuple[str, float, str | None]:
    sorted_caps = sorted(candidate_caps, key=lambda x: x[1], reverse=True)
    top_cap = sorted_caps[0][1]
    top_tied = [name for name, cap in sorted_caps if abs(cap - top_cap) <= 1e-9]
    winner_name = rng.choice(top_tied)

    remaining = [(name, cap) for name, cap in sorted_caps if name != winner_name]
    runner_up = remaining[0][0] if remaining else None
    second_cap = remaining[0][1] if remaining else 0.0

    if runner_up is None:
        clearing = min_increment
    else:
        clearing = min(top_cap, second_cap + min_increment)
    return winner_name, clearing, runner_up


def simulate_auction(
    teams: list[Team],
    odds: dict[str, float],
    payout_rules: dict[str, Any],
    participants: list[dict[str, Any]],
    runs: int,
    seed: int | None,
    min_increment: float,
    force_unlimited_bankroll: bool = False,
    soft_cap_enabled: bool = False,
    soft_cap_decay: float = 4.0,
) -> dict[str, Any]:
    """Simulate open-ascending auction across teams and return ledger + metrics."""

    if runs <= 0:
        raise ValidationError("runs must be > 0")
    if min_increment <= 0:
        raise ValidationError("min_increment must be > 0")
    if soft_cap_decay < 0:
        raise ValidationError("soft_cap_decay must be >= 0")

    validate_auction_participants(
        participants=participants, force_unlimited_bankroll=force_unlimited_bankroll
    )

    rng = Random(seed)
    strengths = odds_to_strengths(odds)
    summary, _ = run_simulations(teams=teams, strengths=strengths, runs=runs, seed=seed)

    default_pot = sum(float(p.get("bankroll") or 0.0) for p in participants)
    explicit_total_pot = float(payout_rules.get("total_pot") or 0.0)
    if explicit_total_pot <= 0 and default_pot <= 0:
        raise ValidationError(
            "payout_rules.total_pot must be > 0 when participants use unlimited bankroll"
        )
    team_ev, total_pot = _team_expected_values(
        finish_counts=summary["finish_counts"],
        total_runs=summary["total_runs"],
        payout_rules=payout_rules,
        default_pot=default_pot,
    )

    states: dict[str, ParticipantState] = {}
    strategies = {}
    for participant in participants:
        name = str(participant["name"])
        unlimited_bankroll = force_unlimited_bankroll or bool(
            participant.get("unlimited_bankroll", False)
        )
        bankroll = float(participant.get("bankroll") or 0.0)
        remaining = float("inf") if unlimited_bankroll else bankroll
        states[name] = ParticipantState(
            name=name,
            bankroll_total=bankroll if bankroll > 0 else None,
            remaining_bankroll=remaining,
            unlimited_bankroll=unlimited_bankroll,
        )
        strategies[name] = build_strategy(participant["strategy"])

    ordered_teams = sorted(teams, key=lambda t: t.slot)
    team_meta = {team.team: team for team in teams}
    ledger: list[AuctionResultLine] = []
    owners: dict[str, str] = {}

    for team in ordered_teams:
        caps: list[tuple[str, float]] = []
        for name, state in states.items():
            if (
                not state.unlimited_bankroll
                and not soft_cap_enabled
                and state.remaining_bankroll < min_increment
            ):
                continue

            context = AuctionContext(
                team=team,
                team_expected_value=team_ev.get(team.team, 0.0),
                min_increment=min_increment,
                participant_count=len(states),
                settings={"seed": seed},
            )
            raw_cap = float(strategies[name].max_bid(context=context, state=state))
            raw_cap = max(0.0, raw_cap)

            cap = raw_cap
            if not state.unlimited_bankroll and not soft_cap_enabled:
                cap = min(state.remaining_bankroll, raw_cap)

            if (
                not state.unlimited_bankroll
                and soft_cap_enabled
                and raw_cap > state.remaining_bankroll
            ):
                # Crossing bankroll is probabilistic: farther above cap means lower likelihood.
                bankroll_base = state.bankroll_total or min_increment
                overshoot = raw_cap - state.remaining_bankroll
                ratio = overshoot / max(bankroll_base, min_increment)
                accept_prob = exp(-soft_cap_decay * ratio)
                if rng.random() >= accept_prob:
                    cap = min(state.remaining_bankroll, raw_cap)

            if cap >= min_increment:
                caps.append((name, cap))

        if not caps:
            ledger.append(AuctionResultLine(team=team.team, winner=None, price=0.0, runner_up=None))
            continue

        winner_name, clearing_price, runner_up = _price_and_winners(
            candidate_caps=caps,
            min_increment=min_increment,
            rng=rng,
        )

        winner_state = states[winner_name]
        winner_state.spend += clearing_price
        winner_state.remaining_bankroll -= clearing_price
        winner_state.teams_won.append(team.team)
        owners[team.team] = winner_name

        ledger.append(
            AuctionResultLine(
                team=team.team,
                winner=winner_name,
                price=clearing_price,
                runner_up=runner_up,
            )
        )

    bidder_summary: dict[str, dict[str, Any]] = {}
    price_by_team = {row.team: row.price for row in ledger}
    for name, state in states.items():
        expected_payout = sum(team_ev.get(team_name, 0.0) for team_name in state.teams_won)
        purchased_team_details = []
        for team_name in sorted(state.teams_won, key=lambda t: team_meta[t].slot):
            team = team_meta[team_name]
            purchased_team_details.append(
                {
                    "team": team.team,
                    "seed": team.seed,
                    "region": team.region,
                    "slot": team.slot,
                    "price": price_by_team.get(team_name, 0.0),
                }
            )
        bidder_summary[name] = {
            "teams_won": len(state.teams_won),
            "owned_teams": sorted(state.teams_won),
            "purchased_teams": purchased_team_details,
            "spend": state.spend,
            "remaining_bankroll": None if state.unlimited_bankroll else state.remaining_bankroll,
            "unlimited_bankroll": state.unlimited_bankroll,
            "expected_payout": expected_payout,
            "expected_profit": expected_payout - state.spend,
        }

    unsold_teams = [row.team for row in ledger if row.winner is None]

    return {
        "settings": {
            "auction_type": "open_ascending",
            "team_order": "bracket_order",
            "min_increment": min_increment,
            "seed": seed,
            "force_unlimited_bankroll": force_unlimited_bankroll,
            "soft_cap_enabled": soft_cap_enabled,
            "soft_cap_decay": soft_cap_decay,
        },
        "winner_ledger": [
            {
                "team": row.team,
                "winner": row.winner,
                "price": row.price,
                "runner_up": row.runner_up,
            }
            for row in ledger
        ],
        "summary_by_bidder": bidder_summary,
        "team_expected_values": team_ev,
        "total_pot": total_pot,
        "unsold_teams": unsold_teams,
        "unsold_count": len(unsold_teams),
        "simulation_summary": summary,
        "ownership": owners,
    }
