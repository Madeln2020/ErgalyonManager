# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 — Makefile
# ═══════════════════════════════════════════════════════════════════
# Quick reference:
#   make up        — Start all infrastructure (PostgreSQL + Redis + MinIO)
#   make down      — Stop infrastructure
#   make backend   — Start the FastAPI dev server
#   make frontend  — Start the Next.js frontend dev server
#   make migrate   — Run Alembic migrations
#   make migrate-new name="msg" — Create a new migration
#   make seed      — Seed sample data
#   make test      — Run backend test suite
#   make clean     — Wipe volumes, caches, and temp files
# ═══════════════════════════════════════════════════════════════════

.PHONY: up down backend frontend migrate migrate-new seed test clean

# ── Infrastructure ─────────────────────────────────────────────────
up:                                                    ## Start all services (PostgreSQL + Redis + MinIO)
	docker compose up -d

up-build:                                              ## Build and start (rebuilds images if needed)
	docker compose up -d --build

down:                                                  ## Stop all services
	docker compose down

logs:                                                  ## Tail logs from all services
	docker compose logs -f

ps:                                                    ## Show service status
	docker compose ps

# ── Backend ────────────────────────────────────────────────────────
backend:                                               ## Start FastAPI dev server with hot-reload
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port $(or $(API_PORT),8887)

backend-deps:                                          ## Install backend Python dependencies
	cd backend && pip install -r requirements.txt

# ── Frontend ───────────────────────────────────────────────────────
frontend:                                              ## Start Next.js dev server
	cd frontend && npm run dev

frontend-deps:                                         ## Install frontend Node dependencies
	cd frontend && npm install

frontend-build:                                        ## Build frontend for production
	cd frontend && npm run build

# ── Database ───────────────────────────────────────────────────────
migrate:                                               ## Apply pending Alembic migrations
	cd backend && alembic upgrade head

migrate-new:                                           ## Create a new auto-generated migration (usage: make migrate-new name="add_something")
	cd backend && alembic revision --autogenerate -m "$(name)"

migrate-downgrade:                                     ## Rollback last migration
	cd backend && alembic downgrade -1

migrate-history:                                       ## Show migration history
	cd backend && alembic history

# ── Seed / Test ────────────────────────────────────────────────────
seed:                                                  ## Seed database with sample data
	cd backend && python -m app.seed

test:                                                  ## Run backend test suite
	cd backend && python -m pytest $(args)

test-coverage:                                         ## Run tests with coverage report
	cd backend && python -m pytest --cov=app --cov-report=term-missing

# ── Maintenance ────────────────────────────────────────────────────
clean:                                                 ## Stop services, wipe volumes, remove caches
	docker compose down -v
	rm -rf backend/__pycache__ frontend/.next
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

python-shell:                                          ## Open a Python shell with the app context
	cd backend && python -c "from app.config import settings; print(settings.model_dump_json(indent=2))"

# ── Help ───────────────────────────────────────────────────────────
help:                                                  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
