"""Build master tournament dataset: one row per team per tournament year.

Combines tournament stage outcomes with seed, conference, and regular season record.
Output: data/master_tourney_dataset.csv
"""

import json

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
KAGGLE = DATA / "march-machine-learning-mania-2026"

# 1. Load base table (one row per team-year in the tournament)
stages = pd.read_csv(DATA / "tourney-results" / "m_team_year_stages.csv")

# 2. Parse seeds: extract numeric seed and region letter
seeds = pd.read_csv(KAGGLE / "MNCAATourneySeeds.csv")
seeds["seed_region"] = seeds["Seed"].str[0]
# Handle seeds like "W01", "W01a", "W01b" (play-in qualifiers)
seeds["seed"] = seeds["Seed"].str[1:3].astype(int)
seeds = seeds.rename(columns={"Season": "season", "TeamID": "team_id"})
stages = stages.merge(seeds[["season", "team_id", "seed", "seed_region"]],
                      on=["season", "team_id"], how="left")

# 3. Join conference affiliations
conf = pd.read_csv(KAGGLE / "MTeamConferences.csv")
conf = conf.rename(columns={"Season": "season", "TeamID": "team_id",
                             "ConfAbbrev": "conference"})
stages = stages.merge(conf[["season", "team_id", "conference"]],
                      on=["season", "team_id"], how="left")

# 4. Aggregate regular season wins and losses
results = pd.read_csv(KAGGLE / "MRegularSeasonCompactResults.csv")
wins = (results.groupby(["Season", "WTeamID"]).size()
        .reset_index(name="reg_season_wins")
        .rename(columns={"Season": "season", "WTeamID": "team_id"}))
losses = (results.groupby(["Season", "LTeamID"]).size()
          .reset_index(name="reg_season_losses")
          .rename(columns={"Season": "season", "LTeamID": "team_id"}))
stages = stages.merge(wins, on=["season", "team_id"], how="left")
stages = stages.merge(losses, on=["season", "team_id"], how="left")

# 5. Compute win percentage
stages["reg_season_wins"] = stages["reg_season_wins"].fillna(0).astype(int)
stages["reg_season_losses"] = stages["reg_season_losses"].fillna(0).astype(int)
total = stages["reg_season_wins"] + stages["reg_season_losses"]
stages["reg_season_win_pct"] = (stages["reg_season_wins"] / total).round(4)

# 6. Compute payout percentages
with open(DATA / "payout_rules.json") as f:
    payout_rules = json.load(f)

finish_pcts = payout_rules["finish_percentages"]
r1_pct = payout_rules["round_one_rules"]["total_percentage"]

stages["payout_pct"] = 0.0

# Later rounds: S16 through CHAMP — equal split among qualifying teams per season
round_map = [
    ("S16", "reached_s16"),
    ("E8", "reached_e8"),
    ("F4", "reached_f4"),
    ("F2", "reached_f2"),
    ("CHAMP", "won_championship"),
]
for stage_key, col in round_map:
    pct = finish_pcts[stage_key]
    counts = stages.groupby("season")[col].transform("sum")
    stages["payout_pct"] += (stages[col] * pct / counts).fillna(0)

# Round 1 payout per season
for season, grp in stages.groupby("season"):
    idx = grp.index
    seeds = grp["seed"]
    won_r32 = grp["reached_r32"]

    # Count 4-12 seed winners
    mask_4_12_won = (seeds >= 4) & (seeds <= 12) & (won_r32 == 1)
    n_4_12_winners = mask_4_12_won.sum()

    # Pool size = 4-12 winners + 8 expected 13-16 covers
    pool_size = n_4_12_winners + 8
    per_team_share = r1_pct / pool_size

    # Seeds 4-12 that won: full share
    stages.loc[idx[mask_4_12_won], "payout_pct"] += per_team_share

    # Seeds 13-16: half share (EV of covering)
    mask_13_16 = (seeds >= 13) & (seeds <= 16)
    stages.loc[idx[mask_13_16], "payout_pct"] += 0.5 * per_team_share

stages["payout_pct"] = stages["payout_pct"].round(6)

# 7. Reorder columns and sort
col_order = [
    "season", "team_id", "team_name",
    "seed", "seed_region", "conference",
    "reg_season_wins", "reg_season_losses", "reg_season_win_pct",
    "reached_playin", "won_playin", "reached_r64", "reached_r32",
    "reached_s16", "reached_e8", "reached_f4", "reached_f2", "won_championship",
    "payout_pct",
]
stages = stages[col_order].sort_values(["season", "seed"]).reset_index(drop=True)

# Write output
out_path = DATA / "master_tourney_dataset.csv"
stages.to_csv(out_path, index=False)

# Verification
print(f"Rows: {len(stages)}")
print(f"Seasons: {stages['season'].min()}–{stages['season'].max()}")
print(f"\nNull counts:\n{stages.isnull().sum()}")
print(f"\n2023 UConn:")
print(stages[(stages["season"] == 2023) & (stages["team_name"] == "UConn")].to_string())
print(f"\nSaved to {out_path}")
