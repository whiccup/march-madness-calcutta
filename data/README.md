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
  - `soft_cap_decay`: optional non-negative float for participant-level soft cap behavior
    - when set, bidder can exceed bankroll with probabilistic penalty (0 = always allow)
  - `strategy`: object with:
    - builtin: `{"kind":"builtin","name":"ev_threshold|flat_discount|seed_bias","params":{...}}`
    - plugin: `{"kind":"plugin","path":"module.path:ClassName","params":{...}}`
- `payout_rules.json`: object with:
  - `total_pot`: numeric
  - `finish_percentages`: map of round key to payout percentage.
  - `round_one_rules`: optional object for seed-specific Round of 64 payout logic:
    - `total_percentage`: total pool share allocated to round-one events
    - `split`: currently supports `equal`
    - `seed_payout_rules`: map of seed buckets to behavior (`EXCLUDE`, `WIN`, `COVER`)
  - `special_percentages`: optional map for non-round awards (for example `BIGGEST_LOSER`).
- `r64_cover_probs.json`: optional list or map of per-team first-round cover probabilities. Required when any round-one seed behavior uses `COVER`.

Valid finish keys: `R64`, `R32`, `S16`, `E8`, `F4`, `F2`, `CHAMP`.
