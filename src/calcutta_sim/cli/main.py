"""Command-line interface for simulation, reporting, and data validation."""

from __future__ import annotations

import argparse
from datetime import datetime, UTC

from calcutta_sim.core.auction import simulate_auction
from calcutta_sim.core.io import load_json, save_json
from calcutta_sim.core.models import Team, parse_team
from calcutta_sim.core.odds import odds_to_strengths
from calcutta_sim.core.portfolio import evaluate_portfolio
from calcutta_sim.core.render import render_ascii_bracket
from calcutta_sim.core.sim import run_simulations
from calcutta_sim.core.validate import (
    ValidationError,
    validate_auction_participants,
    validate_odds,
    validate_payout_rules,
    validate_teams,
)


def _load_teams(path: str) -> list[Team]:
    """Load and parse team records from JSON."""

    raw = load_json(path)
    return [parse_team(item) for item in raw]


def _load_odds(path: str) -> dict[str, float]:
    """Load odds from JSON list or mapping formats."""

    raw = load_json(path)
    if isinstance(raw, list):
        return {str(item["team"]): float(item["championship_odds"]) for item in raw}
    return {str(k): float(v) for k, v in raw.items()}


def _print_champion_probs(summary: dict, limit: int = 20) -> None:
    """Print champion probabilities sorted descending."""

    print("\nChampion probabilities (top teams):")
    sorted_probs = sorted(
        summary["champion_probabilities"].items(), key=lambda x: x[1], reverse=True
    )
    for team, prob in sorted_probs[:limit]:
        print(f"  {team:<25} {prob:>7.2%}")


def _print_round_reach(summary: dict, limit: int = 20) -> None:
    """Print per-round reach probabilities for top teams."""

    print("\nRound reach probabilities (top teams by title odds):")
    sorted_teams = sorted(
        summary["champion_probabilities"].items(), key=lambda x: x[1], reverse=True
    )[:limit]
    for team, _ in sorted_teams:
        rounds = summary["round_reach_probabilities"][team]
        print(
            f"  {team:<25} "
            f"R32 {rounds['R32']:.2%} "
            f"S16 {rounds['S16']:.2%} "
            f"E8 {rounds['E8']:.2%} "
            f"F4 {rounds['F4']:.2%} "
            f"F2 {rounds['F2']:.2%} "
            f"Champ {rounds['CHAMP']:.2%}"
        )


def _print_portfolio(report: dict) -> None:
    """Print formatted portfolio EV and team contribution metrics."""

    print("\nPortfolio summary:")
    print(f"  Total pot:        ${report['total_pot']:.2f}")
    print(f"  Total spend:      ${report['total_spend']:.2f}")
    print(f"  Expected payout:  ${report['expected_payout']:.2f}")
    print(f"  Expected profit:  ${report['expected_profit']:.2f}")

    print("\nTeam expected profit breakdown:")
    for row in report["team_breakdown"]:
        print(
            f"  {row['team']:<25} "
            f"bid ${row['bid_amount']:<8.2f} "
            f"payout ${row['expected_payout']:<8.2f} "
            f"profit ${row['expected_profit']:<8.2f}"
        )


def _print_auction_summary(report: dict) -> None:
    """Print bidder-level auction outcomes and EV metrics."""

    print("\nAuction summary by bidder:")
    for bidder, row in sorted(
        report["summary_by_bidder"].items(), key=lambda x: x[1]["expected_profit"], reverse=True
    ):
        remaining = (
            "unlimited"
            if row.get("unlimited_bankroll")
            else f"${float(row['remaining_bankroll']):.2f}"
        )
        print(
            f"  {bidder:<20} "
            f"teams {row['teams_won']:<2} "
            f"spend ${row['spend']:<9.2f} "
            f"remain {remaining:<10} "
            f"EV payout ${row['expected_payout']:<9.2f} "
            f"EV profit ${row['expected_profit']:<9.2f}"
        )
        if row["purchased_teams"]:
            print("    purchased:")
            for team in row["purchased_teams"]:
                print(
                    f"      {team['team']:<20} "
                    f"seed {team['seed']:<2} "
                    f"region {team['region']:<8} "
                    f"slot {team['slot']:<2} "
                    f"price ${team['price']:.2f}"
                )

    print(f"\nUnsold teams: {report['unsold_count']}")


def cmd_validate_data(args: argparse.Namespace) -> int:
    """Validate input data files and return process exit code."""

    teams = _load_teams(args.teams)
    odds = _load_odds(args.odds)
    validate_teams(teams)
    validate_odds(teams, odds)

    if args.payout_rules:
        payout_rules = load_json(args.payout_rules)
        validate_payout_rules(payout_rules.get("finish_percentages", {}))

    print("Data validation passed.")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Run Monte Carlo simulation, print summary, and optionally save output."""

    teams = _load_teams(args.teams)
    odds = _load_odds(args.odds)

    validate_teams(teams)
    validate_odds(teams, odds)

    strengths = odds_to_strengths(odds)
    summary, sample = run_simulations(teams=teams, strengths=strengths, runs=args.runs, seed=args.seed)

    print(f"Completed {summary['total_runs']} simulations.")
    _print_champion_probs(summary)
    _print_round_reach(summary)

    if args.show_bracket:
        print("\n" + render_ascii_bracket(sample["game_log"]))

    payload = {
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "runs": args.runs,
            "seed": args.seed,
            "model": "weighted_strength_from_championship_odds",
        },
        "summary": summary,
        "sample_bracket": sample,
    }

    if args.bids and args.payout_rules:
        bids = load_json(args.bids)
        payout_rules = load_json(args.payout_rules)
        validate_payout_rules(payout_rules.get("finish_percentages", {}))
        report = evaluate_portfolio(
            bids=bids,
            payout_rules=payout_rules,
            finish_counts=summary["finish_counts"],
            total_runs=summary["total_runs"],
        )
        payload["portfolio"] = report
        _print_portfolio(report)

    if args.output:
        save_json(args.output, payload)
        print(f"\nSaved results to {args.output}")

    return 0


def cmd_portfolio(args: argparse.Namespace) -> int:
    """Compute and print portfolio EV/profit from a saved simulation artifact."""

    bids = load_json(args.bids)
    payout_rules = load_json(args.payout_rules)
    validate_payout_rules(payout_rules.get("finish_percentages", {}))

    sim_results = load_json(args.sim_results)
    summary = sim_results["summary"]
    report = evaluate_portfolio(
        bids=bids,
        payout_rules=payout_rules,
        finish_counts=summary["finish_counts"],
        total_runs=summary["total_runs"],
    )
    _print_portfolio(report)
    return 0


def cmd_render_bracket(args: argparse.Namespace) -> int:
    """Render an ASCII bracket from saved output or a one-off simulation."""

    if args.sim_results:
        sim_results = load_json(args.sim_results)
        game_log = sim_results["sample_bracket"]["game_log"]
        print(render_ascii_bracket(game_log))
        return 0

    teams = _load_teams(args.teams)
    odds = _load_odds(args.odds)
    validate_teams(teams)
    validate_odds(teams, odds)
    strengths = odds_to_strengths(odds)
    _, sample = run_simulations(teams=teams, strengths=strengths, runs=1, seed=args.seed)
    print(render_ascii_bracket(sample["game_log"]))
    return 0


def cmd_simulate_auction(args: argparse.Namespace) -> int:
    """Run open-ascending Calcutta auction simulation and persist results."""

    teams = _load_teams(args.teams)
    odds = _load_odds(args.odds)
    payout_rules = load_json(args.payout_rules)
    participants = load_json(args.participants)

    validate_teams(teams)
    validate_odds(teams, odds)
    validate_payout_rules(payout_rules.get("finish_percentages", {}))
    validate_auction_participants(
        participants=participants,
        force_unlimited_bankroll=args.unlimited_bankroll,
    )

    auction_report = simulate_auction(
        teams=teams,
        odds=odds,
        payout_rules=payout_rules,
        participants=participants,
        runs=args.runs,
        seed=args.seed,
        min_increment=args.min_increment,
        force_unlimited_bankroll=args.unlimited_bankroll,
    )
    _print_auction_summary(auction_report)

    payload = {
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "runs": args.runs,
            "seed": args.seed,
            "model": "open_ascending_expected_value",
        },
        "auction": {
            "settings": auction_report["settings"],
            "winner_ledger": auction_report["winner_ledger"],
            "summary_by_bidder": auction_report["summary_by_bidder"],
            "ownership": auction_report["ownership"],
            "team_expected_values": auction_report["team_expected_values"],
            "total_pot": auction_report["total_pot"],
            "unsold_teams": auction_report["unsold_teams"],
            "unsold_count": auction_report["unsold_count"],
        },
        "simulation_summary": auction_report["simulation_summary"],
    }
    save_json(args.output, payload)
    print(f"\nSaved auction results to {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Create the full argument parser with all subcommands."""

    parser = argparse.ArgumentParser(prog="calcutta-sim")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-data", help="Validate input files")
    validate_parser.add_argument("--teams", default="data/teams.json")
    validate_parser.add_argument("--odds", default="data/odds.json")
    validate_parser.add_argument("--payout-rules")
    validate_parser.set_defaults(func=cmd_validate_data)

    sim_parser = subparsers.add_parser("simulate", help="Run Monte Carlo simulation")
    sim_parser.add_argument("--teams", default="data/teams.json")
    sim_parser.add_argument("--odds", default="data/odds.json")
    sim_parser.add_argument("--runs", type=int, default=10000)
    sim_parser.add_argument("--seed", type=int)
    sim_parser.add_argument("--show-bracket", action="store_true")
    sim_parser.add_argument("--output", default="runs/latest.json")
    sim_parser.add_argument("--bids")
    sim_parser.add_argument("--payout-rules")
    sim_parser.set_defaults(func=cmd_simulate)

    portfolio_parser = subparsers.add_parser(
        "portfolio", help="Evaluate expected payout/profit from simulation output"
    )
    portfolio_parser.add_argument("--bids", default="data/bids.json")
    portfolio_parser.add_argument("--payout-rules", default="data/payout_rules.json")
    portfolio_parser.add_argument("--sim-results", default="runs/latest.json")
    portfolio_parser.set_defaults(func=cmd_portfolio)

    render_parser = subparsers.add_parser("render-bracket", help="Render an ASCII bracket")
    render_parser.add_argument("--sim-results")
    render_parser.add_argument("--teams", default="data/teams.json")
    render_parser.add_argument("--odds", default="data/odds.json")
    render_parser.add_argument("--seed", type=int)
    render_parser.set_defaults(func=cmd_render_bracket)

    auction_parser = subparsers.add_parser(
        "simulate-auction", help="Run open-ascending auction simulation"
    )
    auction_parser.add_argument("--teams", default="data/teams.json")
    auction_parser.add_argument("--odds", default="data/odds.json")
    auction_parser.add_argument("--payout-rules", default="data/payout_rules.json")
    auction_parser.add_argument("--participants", default="data/participants.json")
    auction_parser.add_argument("--runs", type=int, default=10000)
    auction_parser.add_argument("--seed", type=int)
    auction_parser.add_argument("--min-increment", type=float, default=5.0)
    auction_parser.add_argument("--unlimited-bankroll", action="store_true")
    auction_parser.add_argument("--output", default="runs/auction_latest.json")
    auction_parser.set_defaults(func=cmd_simulate_auction)

    return parser


def main() -> int:
    """CLI entrypoint with standardized error handling and exit codes."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        return args.func(args)
    except ValidationError as exc:
        print(f"Validation error: {exc}")
        return 2
    except (KeyError, ValueError, TypeError) as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
