PYTHON ?= python3
PYTHONPATH := src

.PHONY: validate simulate auction auction-soft-cap auction-unlimited auction-unlimited-soft-cap test

validate:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m calcutta_sim validate-data \
		--teams data/teams.json \
		--odds data/odds.json \
		--payout-rules data/payout_rules.json

simulate:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m calcutta_sim simulate \
		--teams data/teams.json \
		--odds data/odds.json \
		--runs 20000 \
		--seed 42 \
		--show-bracket \
		--bids data/bids.json \
		--payout-rules data/payout_rules.json \
		--output runs/latest.json

auction:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m calcutta_sim simulate-auction \
		--teams data/teams.json \
		--odds data/odds.json \
		--participants data/participants.json \
		--payout-rules data/payout_rules.json \
		--runs 20000 \
		--seed 42 \
		--min-increment 5 \
		--output runs/auction_latest.json

auction-soft-cap:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m calcutta_sim simulate-auction \
		--teams data/teams.json \
		--odds data/odds.json \
		--participants data/participants.json \
		--payout-rules data/payout_rules.json \
		--runs 20000 \
		--seed 42 \
		--min-increment 5 \
		--soft-cap-enabled \
		--soft-cap-decay 2.0 \
		--output runs/auction_soft_cap.json

auction-unlimited:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m calcutta_sim simulate-auction \
		--teams data/teams.json \
		--odds data/odds.json \
		--participants data/participants.json \
		--payout-rules data/payout_rules.json \
		--runs 20000 \
		--seed 42 \
		--min-increment 5 \
		--unlimited-bankroll \
		--output runs/auction_unlimited.json

auction-unlimited-soft-cap:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m calcutta_sim simulate-auction \
		--teams data/teams.json \
		--odds data/odds.json \
		--participants data/participants.json \
		--payout-rules data/payout_rules.json \
		--runs 20000 \
		--seed 42 \
		--min-increment 5 \
		--unlimited-bankroll \
		--soft-cap-enabled \
		--soft-cap-decay 2.0 \
		--output runs/auction_unlimited_soft_cap.json

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_*.py'
