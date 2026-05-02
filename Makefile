.DEFAULT_GOAL := help

PY ?= python3.12
VENV ?= backend/.venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
PYRIGHT := $(VENV)/bin/pyright
NEXDOC := $(VENV)/bin/nexdoc

.PHONY: help
help:
	@echo "NexusDocs make targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

.PHONY: install
install: $(VENV)/.installed ## Install backend dependencies into a venv

$(VENV)/.installed: backend/pyproject.toml
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip
	cd backend && ../$(VENV)/bin/pip install -e '.[dev]'
	@touch $(VENV)/.installed

.PHONY: install-frontend
install-frontend: ## Install frontend dependencies (Node)
	cd frontend && npm install --no-audit --no-fund

# ---------------------------------------------------------------------------
# Dev loop
# ---------------------------------------------------------------------------

.PHONY: dev
dev: install ## Run API + seed in-memory repo from sample fixture; serve on :8080
	$(NEXDOC) serve --seed examples/payments-sample.yaml

.PHONY: dev-frontend
dev-frontend: ## Run the Vite dev server on :5173 (proxies /api to :8080)
	cd frontend && npm run dev

# ---------------------------------------------------------------------------
# Tests / lint / types
# ---------------------------------------------------------------------------

.PHONY: test
test: install ## Run backend tests
	cd backend && ../$(VENV)/bin/pytest

.PHONY: test-frontend
test-frontend: ## Type-check the frontend
	cd frontend && node node_modules/typescript/bin/tsc --noEmit

.PHONY: lint
lint: install ## Lint backend with ruff
	cd backend && ../$(VENV)/bin/ruff check .

.PHONY: format
format: install ## Auto-format backend with ruff
	cd backend && ../$(VENV)/bin/ruff format .
	cd backend && ../$(VENV)/bin/ruff check --fix .

.PHONY: typecheck
typecheck: install ## Type-check backend with pyright
	cd backend && ../$(VENV)/bin/pyright

# ---------------------------------------------------------------------------
# Docker compose
# ---------------------------------------------------------------------------

.PHONY: up
up: ## Start the full stack (neo4j + api + ui + seed)
	docker compose up -d --build

.PHONY: down
down: ## Tear down the stack
	docker compose down

.PHONY: downup
downup: ## Tear down and up the stack again
	docker compose down && docker compose up -d --build

.PHONY: logs
logs: ## Tail compose logs
	docker compose logs -f

.PHONY: seed
seed: ## Re-seed Neo4j from the configured SEED_FILE (default: large dataset)
	docker compose run --rm seed

.PHONY: seed-small
seed-small: ## Re-seed Neo4j from the small payments fixture
	SEED_FILE=/examples/payments-sample.yaml docker compose run --rm seed

.PHONY: seed-large
seed-large: examples/large-acme-corp.yaml ## (Re)generate + seed the 1.7k-entity Acme dataset
	SEED_FILE=/examples/large-acme-corp.yaml docker compose run --rm seed

examples/large-acme-corp.yaml: scripts/generate_large_dataset.py
	python3 scripts/generate_large_dataset.py -o $@

# ---------------------------------------------------------------------------
# CLI shortcuts
# ---------------------------------------------------------------------------

.PHONY: apply
apply: install ## Apply the example YAML to a memory repository
	$(NEXDOC) apply examples/payments-sample.yaml

.PHONY: render
render: install ## Render the team.payments view at zoom 35
	$(NEXDOC) --state examples/payments-sample.yaml render team.payments --zoom 35
