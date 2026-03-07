"""Bracket simulation primitives and aggregate statistics helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from random import Random

from calcutta_sim.core.models import ROUND_ORDER, ROUND_RANK, Team
from calcutta_sim.core.odds import win_probability

GAME_ROUNDS = ["R64", "R32", "S16", "E8", "F4", "F2"]
NEXT_ROUND = {
    "R64": "R32",
    "R32": "S16",
    "S16": "E8",
    "E8": "F4",
    "F4": "F2",
    "F2": "CHAMP",
}


@dataclass
class GameResult:
    """Single simulated game result."""

    round_name: str
    team_a: str
    team_b: str
    winner: str
    loser: str
    margin: int


@dataclass
class TournamentResult:
    """Outputs for one simulated tournament run."""

    champion: str
    deepest_round: dict[str, str]
    game_log: list[GameResult]


def _initial_pairings(teams: list[Team]) -> list[tuple[str, str]]:
    """Build first-round pairings from fixed team slot ordering."""

    slot_to_team = {team.slot: team.team for team in teams}
    return [(slot_to_team[i], slot_to_team[i + 1]) for i in range(1, 65, 2)]


def simulate_tournament(
    teams: list[Team], strengths: dict[str, float], rng: Random
) -> TournamentResult:
    """Simulate one full bracket and return champion, finishes, and game log."""

    deepest = {team.team: "R64" for team in teams}
    game_log: list[GameResult] = []

    pairings = _initial_pairings(teams)

    for round_name in GAME_ROUNDS:
        winners: list[str] = []
        next_round = NEXT_ROUND[round_name]
        for team_a, team_b in pairings:
            p_a = win_probability(team_a, team_b, strengths)
            winner = team_a if rng.random() < p_a else team_b
            loser = team_b if winner == team_a else team_a
            expected_margin = 4.0 + 16.0 * abs(p_a - 0.5)
            margin = max(1, int(round(rng.gauss(expected_margin, 7.0))))
            winners.append(winner)

            if ROUND_RANK[next_round] > ROUND_RANK[deepest[winner]]:
                deepest[winner] = next_round

            game_log.append(
                GameResult(
                    round_name=round_name,
                    team_a=team_a,
                    team_b=team_b,
                    winner=winner,
                    loser=loser,
                    margin=margin,
                )
            )

        if len(winners) == 1:
            pairings = [(winners[0], winners[0])]
            break

        pairings = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]

    champion = pairings[0][0]
    return TournamentResult(champion=champion, deepest_round=deepest, game_log=game_log)


def aggregate_results(results: list[TournamentResult]) -> dict:
    """Aggregate many tournament runs into probabilities and finish counts."""

    if not results:
        raise ValueError("No results to aggregate")

    total_runs = len(results)
    champion_counts = defaultdict(int)
    finish_counts = defaultdict(lambda: defaultdict(int))

    for result in results:
        champion_counts[result.champion] += 1
        for team, finish in result.deepest_round.items():
            finish_counts[team][finish] += 1

    champion_probabilities = {
        team: count / total_runs for team, count in sorted(champion_counts.items())
    }

    round_reach_probabilities: dict[str, dict[str, float]] = defaultdict(dict)
    for team, per_finish in finish_counts.items():
        for round_name in ROUND_ORDER:
            reached = sum(
                count
                for finish, count in per_finish.items()
                if ROUND_RANK[finish] >= ROUND_RANK[round_name]
            )
            round_reach_probabilities[team][round_name] = reached / total_runs

    return {
        "total_runs": total_runs,
        "champion_probabilities": champion_probabilities,
        "finish_counts": {team: dict(counts) for team, counts in finish_counts.items()},
        "round_reach_probabilities": dict(round_reach_probabilities),
    }
