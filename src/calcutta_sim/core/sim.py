from __future__ import annotations

from random import Random

from calcutta_sim.core.bracket import aggregate_results, simulate_tournament
from calcutta_sim.core.models import Team


def run_simulations(
    teams: list[Team], strengths: dict[str, float], runs: int, seed: int | None
) -> tuple[dict, dict]:
    if runs <= 0:
        raise ValueError("runs must be > 0")

    rng = Random(seed)
    raw_results = [simulate_tournament(teams=teams, strengths=strengths, rng=rng) for _ in range(runs)]
    summary = aggregate_results(raw_results)

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
            }
            for g in sample.game_log
        ],
    }
    return summary, sample_payload
