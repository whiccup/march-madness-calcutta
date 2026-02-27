"""Module entrypoint for running the CLI via ``python -m calcutta_sim``."""

from calcutta_sim.cli.main import main


if __name__ == "__main__":
    raise SystemExit(main())
