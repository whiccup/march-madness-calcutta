"""Build Calcutta auction master dataset: one row per team per auction year.

Merges auction bids (with mapped Kaggle team IDs) against tournament outcomes,
seeds, and payout percentages to produce a single analysis-ready CSV.

Output: data/calcutta_master.csv
"""

import json

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
KAGGLE = DATA / "march-machine-learning-mania-2026"

# ── 1. Load auction data (with team IDs already mapped) ──────────────────────
mapped = pd.read_csv(DATA / "calcutta-historical" / "calcutta_with_team_ids.csv")
mapped = mapped[mapped["year"].astype(str).isin(["2024", "2025"])].copy()
mapped["year"] = pd.to_numeric(mapped["year"], errors="coerce").astype("Int64")
mapped["seed"] = pd.to_numeric(mapped["seed"], errors="coerce")
mapped["winning_bid"] = pd.to_numeric(mapped["winning_bid"], errors="coerce")
for col in ["team_id_primary", "team_id_a", "team_id_b"]:
    mapped[col] = pd.to_numeric(mapped[col], errors="coerce").astype("Int64")

# ── 2. Load tournament stages ────────────────────────────────────────────────
stages = pd.read_csv(DATA / "tourney-results" / "m_team_year_stages.csv")
stages["season"] = pd.to_numeric(stages["season"], errors="coerce").astype("Int64")
stages["team_id"] = pd.to_numeric(stages["team_id"], errors="coerce").astype("Int64")

STAGE_FLAG_COLS = [
    "won_playin", "reached_r64", "reached_r32", "reached_s16",
    "reached_e8", "reached_f4", "reached_f2", "won_championship",
]
stages_flags = stages[["season", "team_id"] + STAGE_FLAG_COLS].copy()

# ── 3. Resolve play-in combo rows to a single team_id_effective ──────────────
# For combo rows (team_id_a + team_id_b), pick the team that advanced further.

def _advancement_score(row, suffix):
    """Score how far a team advanced (higher = further)."""
    return (
        row.get(f"won_playin{suffix}", 0) * 100
        + row.get(f"reached_r64{suffix}", 0) * 50
        + row.get(f"reached_r32{suffix}", 0) * 25
        + row.get(f"reached_s16{suffix}", 0) * 12
        + row.get(f"reached_e8{suffix}", 0) * 6
        + row.get(f"reached_f4{suffix}", 0) * 3
        + row.get(f"reached_f2{suffix}", 0) * 2
        + row.get(f"won_championship{suffix}", 0)
    )


combo = mapped[["year", "team_name", "team_id_primary", "team_id_a", "team_id_b"]].copy()

# Join stage flags for team_a and team_b
combo = combo.merge(
    stages_flags, how="left",
    left_on=["year", "team_id_a"], right_on=["season", "team_id"],
).drop(columns=["season", "team_id"])

combo = combo.merge(
    stages_flags, how="left",
    left_on=["year", "team_id_b"], right_on=["season", "team_id"],
    suffixes=("_a", "_b"),
).drop(columns=["season", "team_id"])

for col in STAGE_FLAG_COLS:
    combo[f"{col}_a"] = pd.to_numeric(combo[f"{col}_a"], errors="coerce").fillna(0)
    combo[f"{col}_b"] = pd.to_numeric(combo[f"{col}_b"], errors="coerce").fillna(0)

score_a = combo.apply(lambda r: _advancement_score(r, "_a"), axis=1)
score_b = combo.apply(lambda r: _advancement_score(r, "_b"), axis=1)

combo["team_id_effective"] = combo["team_id_primary"]
needs = combo["team_id_effective"].isna()
combo.loc[needs & (score_a >= score_b), "team_id_effective"] = combo.loc[
    needs & (score_a >= score_b), "team_id_a"
]
combo.loc[needs & (score_b > score_a), "team_id_effective"] = combo.loc[
    needs & (score_b > score_a), "team_id_b"
]
combo["team_id_effective"] = combo["team_id_effective"].astype("Int64")

# Merge effective ID back into mapped
mapped = mapped.merge(
    combo[["year", "team_name", "team_id_effective"]],
    how="left", on=["year", "team_name"],
)

# ── 4. Join tournament stage flags ───────────────────────────────────────────
df = mapped.merge(
    stages_flags, how="left",
    left_on=["year", "team_id_effective"], right_on=["season", "team_id"],
).drop(columns=["season", "team_id"])

# ── 5. Join canonical team names and seed codes ──────────────────────────────
teams = pd.read_csv(KAGGLE / "MTeams.csv")
teams_lookup = teams[["TeamID", "TeamName"]].rename(
    columns={"TeamID": "team_id_effective", "TeamName": "team_name_kaggle"}
)
df = df.merge(teams_lookup, how="left", on="team_id_effective")
df["team_name"] = df["team_name_kaggle"].fillna(df["team_name"])

seeds = pd.read_csv(KAGGLE / "MNCAATourneySeeds.csv")
seeds["seed_region"] = seeds["Seed"].str[0]
seeds["seed_num"] = seeds["Seed"].str[1:3].astype(int)
seeds = seeds.rename(columns={"Season": "year", "TeamID": "team_id_effective"})
seeds["year"] = seeds["year"].astype("Int64")
seeds["team_id_effective"] = seeds["team_id_effective"].astype("Int64")

df = df.merge(
    seeds[["year", "team_id_effective", "seed_region", "seed_num"]],
    how="left", on=["year", "team_id_effective"],
)
df["seed"] = df["seed_num"].fillna(df["seed"]).astype(int)

# ── 6. Join conference from master dataset ───────────────────────────────────
master = pd.read_csv(DATA / "master_tourney_dataset.csv")
master_cols = master[["season", "team_id", "conference", "payout_pct"]].copy()
master_cols["season"] = master_cols["season"].astype("Int64")
master_cols["team_id"] = master_cols["team_id"].astype("Int64")

df = df.merge(
    master_cols, how="left",
    left_on=["year", "team_id_effective"], right_on=["season", "team_id"],
).drop(columns=["season", "team_id"])

# ── 7. Compute derived columns ──────────────────────────────────────────────
with open(DATA / "payout_rules.json") as f:
    payout_rules = json.load(f)
total_pot = payout_rules["total_pot"]

df["payout_dollars"] = (df["payout_pct"] * total_pot).round(2)
df["roi"] = ((df["payout_dollars"] - df["winning_bid"]) / df["winning_bid"]).round(4)

# furthest_round: int 0-6 from stage flags
round_cols = ["reached_r64", "reached_r32", "reached_s16", "reached_e8",
              "reached_f4", "reached_f2", "won_championship"]
df["furthest_round"] = 0
for i, col in enumerate(round_cols):
    df.loc[df[col] == 1, "furthest_round"] = i

# ── 8. Select and sort ──────────────────────────────────────────────────────
col_order = [
    "season_year", "team_id_effective", "team_name", "seed", "seed_region",
    "region", "conference",
    "winning_bid", "owner_name",
    "reached_r64", "reached_r32", "reached_s16", "reached_e8",
    "reached_f4", "reached_f2", "won_championship",
    "furthest_round", "payout_pct", "payout_dollars", "roi",
]

df = df.rename(columns={"year": "season", "team_id_effective": "team_id"})
col_order = [c.replace("season_year", "season").replace("team_id_effective", "team_id")
             for c in col_order]

df = df[col_order].sort_values(["season", "seed"]).reset_index(drop=True)

# ── 9. Write output ─────────────────────────────────────────────────────────
out_path = DATA / "calcutta_master.csv"
df.to_csv(out_path, index=False)

# Verification
print(f"Rows: {len(df)}")
print(f"Seasons: {sorted(df['season'].unique())}")
join_rate = df["reached_r64"].notna().mean()
print(f"Stage join rate: {join_rate:.1%}")
print(f"\nSample row:\n{df.iloc[0].to_string()}")
print(f"\nSaved to {out_path}")
