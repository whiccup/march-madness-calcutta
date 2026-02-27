# march-madness-calcutta

March Madness simulations with Calcutta modeling.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

## Commands

Validate inputs:

```bash
python -m calcutta_sim validate-data \
  --teams data/teams.json \
  --odds data/odds.json \
  --payout-rules data/payout_rules.json
```

Run simulation and save outputs:

```bash
python -m calcutta_sim simulate \
  --teams data/teams.json \
  --odds data/odds.json \
  --runs 20000 \
  --seed 42 \
  --show-bracket \
  --bids data/bids.json \
  --payout-rules data/payout_rules.json \
  --output runs/latest.json
```

Run Calcutta auction-space simulation:

```bash
python -m calcutta_sim simulate-auction \
  --teams data/teams.json \
  --odds data/odds.json \
  --participants data/participants.json \
  --payout-rules data/payout_rules.json \
  --runs 20000 \
  --seed 42 \
  --min-increment 5 \
  --output runs/auction_latest.json
```

Enable unlimited bankroll globally for all participants:

```bash
python -m calcutta_sim simulate-auction \
  --participants data/participants.json \
  --payout-rules data/payout_rules.json \
  --unlimited-bankroll
```

Enable soft bankroll cap (participants can exceed cap with probability penalty):

```bash
python -m calcutta_sim simulate-auction \
  --participants data/participants.json \
  --payout-rules data/payout_rules.json \
  --soft-cap-enabled \
  --soft-cap-decay 2.0
```

Per-participant soft cap is also supported directly in `participants.json`:

```json
{
  "name": "RiskTaker",
  "bankroll": 300,
  "soft_cap_decay": 1.5,
  "strategy": { "kind": "builtin", "name": "ev_threshold", "params": { "aggressiveness": 1.2 } }
}
```

Evaluate portfolio from a saved run:

```bash
python -m calcutta_sim portfolio \
  --bids data/bids.json \
  --payout-rules data/payout_rules.json \
  --sim-results runs/latest.json
```

Render bracket from saved run:

```bash
python -m calcutta_sim render-bracket --sim-results runs/latest.json
```

## Tests

```bash
PYTHONPATH=src pytest
```
