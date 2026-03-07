"""Top-level Monte Carlo simulation orchestration."""

from __future__ import annotations

from collections import defaultdict
from random import Random
from typing import Any

from calcutta_sim.core.bracket import aggregate_results, simulate_tournament
from calcutta_sim.core.models import Team
from calcutta_sim.core.payout import biggest_loser_percentage, get_seed_rule_map, round_one_total_percentage


def run_simulations(
    teams: list[Team],
    strengths: dict[str, float],
    runs: int,
    seed: int | None,
    payout_rules: dict[str, Any] | None = None,
    r64_cover_probabilities: dict[str, float] | None = None,
) -> tuple[dict, dict]:
    """Run multiple bracket simulations and return summary plus one sample path."""

    if runs <= 0:
        raise ValueError("runs must be > 0")

    payout_rules = payout_rules or {}
    rng = Random(seed)
    raw_results = []

    team_by_name = {team.team: team for team in teams}
    seed_rules = get_seed_rule_map(payout_rules)
    use_round1 = round_one_total_percentage(payout_rules) > 0
    use_biggest_loser = biggest_loser_percentage(payout_rules) > 0

    round1_share_sums: dict[str, float] = defaultdict(float)
    biggest_loser_share_sums: dict[str, float] = defaultdict(float)
    sample_r64_covers: dict[str, bool] = {}

    for run_idx in range(runs):
        result = simulate_tournament(teams=teams, strengths=strengths, rng=rng)
        raw_results.append(result)

        r64_covers: dict[str, bool] = {}
        qualifiers: set[str] = set()
        if use_round1:
            for game in result.game_log:
                if game.round_name != "R64":
                    continue
                for team_name in (game.team_a, game.team_b):
                    seed = team_by_name[team_name].seed
                    behavior = seed_rules.get(seed, "EXCLUDE")
                    if behavior == "EXCLUDE":
                        continue
                    if behavior == "WIN":
                        if game.winner == team_name:
                            qualifiers.add(team_name)
                        continue
                    if behavior == "COVER":
                        cover_prob = float((r64_cover_probabilities or {}).get(team_name, 0.0))
                        did_cover = rng.random() < cover_prob
                        r64_covers[team_name] = did_cover
                        if did_cover:
                            qualifiers.add(team_name)
                        continue

            if qualifiers:
                share = 1.0 / len(qualifiers)
                for team_name in qualifiers:
                    round1_share_sums[team_name] += share

        if use_biggest_loser:
            biggest_margin = max(game.margin for game in result.game_log)
            biggest_losers = {game.loser for game in result.game_log if game.margin == biggest_margin}
            share = 1.0 / len(biggest_losers)
            for team_name in biggest_losers:
                biggest_loser_share_sums[team_name] += share

        if run_idx == 0:
            sample_r64_covers = dict(r64_covers)

    summary = aggregate_results(raw_results)
    summary["special_event_shares"] = {
        "ROUND1": {team: value / runs for team, value in round1_share_sums.items()},
        "BIGGEST_LOSER": {
            team: value / runs for team, value in biggest_loser_share_sums.items()
        },
    }

    sample = raw_results[0]
    sample_payload = {
        "champion": sample.champion,
        "deepest_round": sample.deepest_round,
        "game_log": [
            {
                "round": g.round_name,
                "team_a": g.team_a,
                "team_b": g.team_b,
                "winner": g.winner,
                "loser": g.loser,
                "margin": g.margin,
            }
            for g in sample.game_log
        ],
        "r64_covers": sample_r64_covers,
    }
    return summary, sample_payload
