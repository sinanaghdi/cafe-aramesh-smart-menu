.PHONY: up down logs test lint format-check db-migrate seed frontend-dev

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

test:
	cd backend && pytest

lint:
	cd backend && ruff check . && mypy app
	cd frontend && npm install && npm run lint && npm run typecheck

format-check:
	cd frontend && npm install && npm run format:check

db-migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m app.db.seed

frontend-dev:
	cd frontend && npm install && npm run dev
