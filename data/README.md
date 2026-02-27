# Data Files

- `teams.json`: array of 64 team objects with `team`, `seed`, `region`, `slot` (1..64).
- `odds.json`: array of objects with `team`, `championship_odds`.
  - Values `>1` are treated as decimal odds.
  - Values `<=1` are treated as implied probabilities.
- `bids.json`: array of objects with `team`, `bid_amount`.
- `payout_rules.json`: object with:
  - `total_pot`: numeric
  - `finish_percentages`: map of round key to payout percentage.

Valid finish keys: `R64`, `R32`, `S16`, `E8`, `F4`, `F2`, `CHAMP`.
