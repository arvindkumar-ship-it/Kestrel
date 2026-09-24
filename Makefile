.PHONY: install lint format format-check typecheck test test-cov migrate migrate-down \
	migrate-cycle up down logs build clean

PYTHON ?= python
PYTHONPATH_API := PYTHONPATH=apps/api

install:
	$(PYTHON) -m pip install --upgrade pip
	pip install -e ".[dev]"

lint:
	ruff check .

format:
	ruff format .

format-check:
	ruff format --check .

typecheck:
	mypy apps/api/app

test:
	pytest -q --asyncio-mode=auto

test-cov:
	pytest -q --cov=app --cov-report=term-missing

# Requires DATABASE_URL to point at a reachable Postgres instance
# (see `make up` to start one locally via docker-compose).
migrate:
	$(PYTHONPATH_API) alembic upgrade head

migrate-down:
	$(PYTHONPATH_API) alembic downgrade -1

# Mirrors the CI migration-verification job: upgrade, downgrade one step,
# upgrade again, to catch irreversible/broken downgrade() implementations.
migrate-cycle:
	$(PYTHONPATH_API) alembic upgrade head
	$(PYTHONPATH_API) alembic downgrade -1
	$(PYTHONPATH_API) alembic upgrade head

up:
	docker compose up --build -d
	@echo "api:    http://localhost:8000"
	@echo "health: http://localhost:8000/health/live"

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
