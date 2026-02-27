# Data Files

- `teams.json`: array of 64 team objects with `team`, `seed`, `region`, `slot` (1..64).
- `odds.json`: array of objects with `team`, `championship_odds`.
  - Values `>1` are treated as decimal odds.
  - Values `<=1` are treated as implied probabilities.
- `bids.json`: array of objects with `team`, `bid_amount`.
- `participants.json`: array of auction participants with:
  - `name`: unique bidder name
  - `bankroll`: positive numeric budget cap (optional when `unlimited_bankroll: true`)
  - `unlimited_bankroll`: optional boolean to remove spend cap for that participant
  - `strategy`: object with:
    - builtin: `{"kind":"builtin","name":"ev_threshold|flat_discount|seed_bias","params":{...}}`
    - plugin: `{"kind":"plugin","path":"module.path:ClassName","params":{...}}`
- `payout_rules.json`: object with:
  - `total_pot`: numeric
  - `finish_percentages`: map of round key to payout percentage.
  - `special_percentages`: optional map for non-round awards (for example `BIGGEST_LOSER`).

Valid finish keys: `R64`, `R32`, `S16`, `E8`, `F4`, `F2`, `CHAMP`.
