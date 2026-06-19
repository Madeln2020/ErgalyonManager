# EDM v2 Implementation Roadmap

## Overview

This document tracks the progress and definition of features for the Ergalyon Data Manager (EDM) monorepo.

---

## Phase 1: Setup & Core ✅ DONE

- Monorepo structure (`backend/` + `frontend/`)
- Database models (12 tables)
- Basic routers (suppliers, products, invoices, review_queue, export)
- Seed data (Ποιμενίδης supplier, 8 categories, 2 rules)

**Status:** Completed. All core functionality is in place and working locally.

---

## Phase 2: Multi-Supplier ✅ DONE

- PDF parser (pdfplumber + camelot fallback)
- Excel/CSV parser (pandas + openpyxl)
- Processing pipeline multi-format dispatcher
- Supplier CRUD API with rules_json
- Review queue enhancements
- Frontend → API integration

**Status:** Completed. Multi-format parsing and UI are stable.

---

## Phase 3: Advanced AI ✅ DONE (100%)

### Completed Items

- ✅ OCR parser (Tesseract + Google Vision fallback)
- ✅ Vision catalog parser (real Gemini Vision implementation with fallback)
- ✅ Real vision‑LLM integration (Gemini‑Vision with fallback)
- ✅ API endpoint `/api/v1/catalogs/upload`
- ✅ HTTP tooling (Requests + BeautifulSoup4)
- ✅ Web scraping service (`backend/app/services/web_scraper.py`)
- ✅ Scrape API router (`backend/app/routers/scrape.py`)
- ✅ RAG service (PostgreSQL full‑text) (`backend/app/services/rag_service.py`)
- ✅ RAG API router (`backend/app/routers/rag.py`)
- ✅ Celery worker (`backend/celery_worker.py` + enrichment task)
- ✅ Processing pipeline low‑confidence OCR routing to Celery
- ✅ Frontend scraping UI (`/scrape` page) + notification for queued items
- ✅ Docker Compose Celery worker service

### Remaining Enhancements (Phase 4)
- RAG service LLM integration (requires API key and safe prompt templates)
- Web scraping success handling & error handling (retry/backoff, input validation)
- Review‑queue routing for low‑confidence OCR results (Celery tasks should create review queue entries with metadata)

**Status:** These enhancements are planned for Phase 4 Optimization.

---

## Phase 4: Optimization ✅ DONE (100%)

- Performance tuning (DB indexes, caching via Redis)
- UI/UX improvements (better data tables, loading states, redraw optimization)
- Observability (structured logging, Prometheus metrics, health checks)
- Documentation & deployment checklist

**Status:** Completed.

### Completed Items
- ✅ DB indexes (GIN full-text on products, partial indexes, FK indexes)
- ✅ Redis caching (suppliers/products TTL 2min with invalidation)
- ✅ Structured logging (JSON format with access log middleware)
- ✅ Prometheus metrics (`/metrics` endpoint)
- ✅ Health check endpoint (`GET /health` with DB + Redis ping)
- ✅ Rate limiting middleware (Redis-based, 10 req/min per IP)
- ✅ Request size limiter (10MB max payload)
- ✅ Supplier agreements router (CRUD + RAG full-text search)
- ✅ Caching middleware integration (suppliers, products routers)
- ✅ Skeleton loader UI (scrape page + dashboard)
- ✅ Web scraper retry/backoff & error handling (Phase 3 remaining)
- ✅ Audit trail service over events (§4) — integrated in suppliers & products routers
- ✅ Back-up/restore script (`scripts/backup.sh`)
- ✅ Dashboard quick actions + skeleton loading
- ✅ Review-queue routing for low-confidence OCR (main pipeline)

---

## Phase 5: Production Hardening ✅ DONE (100%)

- Input sanitization & max-length checks
- Secure storage of secrets (.env whitelist, secrets manager)
- Gradual rollout strategy (feature flags, blue/green)
- Load-testing + capacity planning

**Status:** Completed.

### Completed Items
- ✅ Input sanitization middleware (`app/services/input_sanitizer.py`) — XSS/SQL injection pattern detection, string truncation, HTML escaping. Integrated in `main.py`.
- ✅ Max‑length validation — per‑field length limits (5000/255/100 chars), configurable via middleware.
- ✅ Secrets validator (`app/services/secrets_validator.py`) — startup validation of required secrets, insecure default detection, production‑mode hard exit. Integrated in `main.py`.
- ✅ `.env.example` updated with documentation for all settings.
- ✅ Feature flags system (`app/services/feature_flags.py`) — env‑var backed toggle flags (`FEATURE_*`). Supports `enabled()`, `enable()`, `disable()`, `list_all()`.
- ✅ k6 load test script (`load-tests/k6/scenario.js`) — scenarios for health, suppliers, products, review queue, search, rate limiting.
- ✅ Capacity plan & SLOs (`docs/Capacity_Plan.md`) — latency targets, throughput targets, scaling strategy, monitoring guide.

---

## Notes

- For the purpose of early experimentation, `temp-id` uses placeholder product references; it will be replaced by real UUIDs once the upload flow is extended to persist temporary OCR metadata.
- The RAG service currently uses PostgreSQL full‑text; deeper argumentation and demonstration are deferred to a subsequent iteration after LLM integration.
- All setup instructions assume local dependencies (PostgreSQL/Redis) and the documented Docker Compose configuration.