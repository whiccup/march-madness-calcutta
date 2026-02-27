"""ASCII rendering utilities for simulated bracket outputs."""

from __future__ import annotations

from collections import defaultdict


def render_ascii_bracket(game_log: list[dict]) -> str:
    """Render a round-by-round text bracket from a simulated game log."""

    by_round: dict[str, list[dict]] = defaultdict(list)
    round_order = ["R64", "R32", "S16", "E8", "F4", "F2"]

    for game in game_log:
        by_round[game["round"]].append(game)

    lines: list[str] = ["=== Sample Tournament Bracket ==="]
    for round_name in round_order:
        lines.append("")
        lines.append(f"[{round_name}]")
        games = by_round.get(round_name, [])
        for idx, game in enumerate(games, start=1):
            winner = game["winner"]
            team_a = game["team_a"]
            team_b = game["team_b"]
            lines.append(f"{idx:>2}. {team_a} vs {team_b} -> {winner}")

    if by_round.get("F2"):
        lines.append("")
        lines.append(f"Champion: {by_round['F2'][0]['winner']}")

    return "\n".join(lines)
