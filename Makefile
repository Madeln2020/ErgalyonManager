.PHONY: dev up down db backend frontend migrate seed test clean

# Start infrastructure (PostgreSQL + Redis)
up:
	docker compose up -d

# Stop infrastructure
down:
	docker compose down

# Start backend dev server
backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8887

# Start frontend dev server
frontend:
	cd frontend && npm run dev

# Full dev environment
dev: up backend

# Database migrations
migrate:
	cd backend && alembic upgrade head

migrate-new:
	cd backend && alembic revision --autogenerate -m "$(name)"

# Seed sample data
seed:
	cd backend && python -m app.seed

# Run tests
test:
	cd backend && python -m pytest

# Clean up
clean:
	docker compose down -v
	rm -rf backend/__pycache__ frontend/.next
