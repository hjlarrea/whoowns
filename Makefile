VENV ?= .venv
PYTHON ?= $(VENV)/bin/python

.PHONY: db dev docker-down docker-logs docker-seed docker-up install seed test

$(PYTHON):
	python -m venv $(VENV)

install: $(PYTHON)
	$(PYTHON) -m pip install -r requirements.txt

db:
	docker compose up -d db

dev: install
	PYTHONPATH=src $(PYTHON) -m uvicorn whoowns.api:app --reload

seed: install
	$(PYTHON) -m whoowns.seed

test: install
	$(PYTHON) -m pytest

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api db

docker-seed:
	docker compose exec -T api python -m whoowns.seed
