# Repository Guidelines

## Project Structure & Module Organization
This project uses a `src` layout for Python code and a separate `tests` package.

- `src/calcutta_sim/cli/`: CLI entrypoint and command wiring (`main.py`).
- `src/calcutta_sim/core/`: simulation, bracket logic, validation, I/O, and portfolio logic.
- `tests/`: unit and CLI integration tests (`test_*.py`).
- `data/`: sample input files (`teams.json`, `odds.json`, `bids.json`, `payout_rules.json`).
- `runs/`: generated simulation outputs (for example `runs/latest.json`).

## Build, Test, and Development Commands
Set up a local environment and install in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

Key commands:

- `python -m calcutta_sim validate-data --teams data/teams.json --odds data/odds.json --payout-rules data/payout_rules.json`: validate input integrity.
- `python -m calcutta_sim simulate --teams data/teams.json --odds data/odds.json --runs 20000 --seed 42 --bids data/bids.json --payout-rules data/payout_rules.json --output runs/latest.json`: run simulations and write results.
- `python -m calcutta_sim portfolio --bids data/bids.json --payout-rules data/payout_rules.json --sim-results runs/latest.json`: evaluate bidder outcomes.
- `PYTHONPATH=src pytest`: run all tests.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation.
- Use snake_case for functions/modules/variables, PascalCase for classes, and UPPER_CASE for constants.
- Keep domain logic in `core/`; keep CLI concerns in `cli/`.
- Prefer type hints and small, single-purpose functions.

## Testing Guidelines
- Testing framework: `pytest` (configured in `pyproject.toml`).
- Place tests in `tests/` and name files `test_*.py`.
- Name test functions by behavior, e.g. `test_simulate_respects_seed()`.
- Add or update tests for every behavior change, especially for odds, payout, and validation logic.

## Commit & Pull Request Guidelines
Current history uses short, imperative messages (for example: `mock data`, `doc strings`, `scaffolding done, simulations`). Keep commits focused and descriptive.

For pull requests:
- Explain what changed and why.
- Reference related issues/tasks.
- Include CLI examples or sample output when behavior changes.
- Confirm tests pass locally (`PYTHONPATH=src pytest`) before requesting review.
