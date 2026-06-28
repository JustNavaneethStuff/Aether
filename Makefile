.PHONY: install lint format typecheck test up up-core down logs migrate seed demo

install:
	uv sync --all-packages

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy packages/aether-common/src services

test:
	uv run pytest -v

test-integration:
	uv run pytest tests/integration -v

up:
	docker compose -f docker/docker-compose.yml up -d --build

up-core:
	docker compose -f docker/docker-compose.yml --profile core up -d --build

up-obs:
	docker compose -f docker/docker-compose.yml --profile observability up -d --build

down:
	docker compose -f docker/docker-compose.yml down -v

logs:
	docker compose -f docker/docker-compose.yml logs -f

migrate:
	docker compose -f docker/docker-compose.yml exec memory-service uv run alembic upgrade head

seed:
	uv run python scripts/seed_dev_data.py

demo:
	bash scripts/demos/run-all.sh
