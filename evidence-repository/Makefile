.PHONY: up down migrate test lint verify

up:
	docker compose up -d --build

down:
	docker compose down -v

migrate:
	docker compose exec api alembic upgrade head

test:
	docker compose exec api pytest --cov=evidence_repo --cov-report=term-missing -q

lint:
	docker compose exec api ruff check src tests
	docker compose exec api mypy src

verify:
	curl -s http://localhost:8000/healthz
