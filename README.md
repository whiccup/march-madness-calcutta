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
