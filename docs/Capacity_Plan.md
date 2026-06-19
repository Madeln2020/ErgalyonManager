# EDM v2 — Capacity Plan & SLOs

## Overview

This document defines the expected capacity, performance targets, and
Service Level Objectives (SLOs) for the EDM v2 system in production.

## Architecture
```
User → Nginx / LB (optional) → FastAPI (uvicorn) → PostgreSQL
                                        ↓
                                     Redis (cache, queue, rate limit)
                                        ↓
                                  Celery worker (async enrichment)
```

## Expected Load (per month)

| Metric | Current | 6‑month target | 12‑month target |
|--------|---------|----------------|-----------------|
| Suppliers onboarded | 1 (Ποιμενίδης) | 10 | 30 |
| Invoices processed | ~100 | 1,000 | 5,000 |
| Products catalogued | ~2,000 | 20,000 | 100,000 |
| Active users (internal) | 1‑3 | 5‑10 | 20‑50 |

## Service Level Objectives (SLOs)

### API Latency (p95)

| Endpoint | Target (p95) | Measured at |
|----------|-------------|-------------|
| `GET /health` | < 500ms | Application middleware |
| `GET /api/v1/suppliers` | < 1s (cached: < 50ms) | k6 + Prometheus |
| `GET /api/v1/products` | < 2s (cached: < 100ms) | k6 + Prometheus |
| `GET /api/v1/review-queue` | < 1s | k6 + Prometheus |
| `POST /api/v1/invoices/upload` | < 5s (sync parse) | Application timer |

### Throughput

| Scenario | Target |
|----------|--------|
| Concurrent API users | 10‑20 without degradation |
| Maximum invoice uploads/min | 30 (1 per 2s) |
| Maximum scrape requests/min | 60 (rate limited to 10/user/min) |

### Availability

| Component | Uptime target |
|-----------|---------------|
| Application (API) | 99.5% (≈3.5h downtime/month allowed) |
| Database | 99.9% |
| Cache (Redis) | 99.0% (graceful degradation when down) |

## Bottlenecks & Mitigations

### 1. PostgreSQL — Sequential scans on product search

**Current status:** GIN indexes on `description` and `description_normalized`
already created (migration `004_perf_indexes.py`).

**Next steps:**
- Monitor `pg_stat_user_tables.seq_scan` via Prometheus
- Add composite indexes if new query patterns emerge
- Consider partitioning `audit_log` by month if it exceeds 1M rows

### 2. PDF/OCR parsing — CPU‑intensive on main thread

**Current status:** Parsing happens synchronously in the API request.

**Mitigation:**
- Offload OCR and large PDF parsing to Celery workers (already
  configured in `docker-compose.yml`)
- Result polling: upload returns `202 Accepted` + job ID, frontend
  polls until complete

### 3. Redis — Single point of failure for caching + rate limiting

**Current status:** All Redis functions degrade gracefully (caching
skipped, rate limiting disabled) if Redis is down.

**Mitigation:**
- Redis Sentinel or cluster for high availability if Redis becomes
  critical
- Separate rate‑limiter Redis from cache Redis if scale requires

## Scaling Strategy

### Vertical (first)

- Increase PostgreSQL `shared_buffers` / `work_mem`
- Add more CPU/RAM to the API server
- Increase `uvicorn --workers N` up to 2× CPU cores

### Horizontal (when needed)

```
                  ┌──────────┐
Load balancer ───→│ API node 1│──→ PostgreSQL (primary)
                  ├──────────┤        ↓
                  │ API node 2│──→ PostgreSQL (read replica)
                  ├──────────┤
                  │ API node N│
                  └──────────┘
```

- Stateless API → add more `uvicorn` workers or container replicas
- Read replicas for product queries, writes go to primary
- Celery worker pool auto‑scales with Redis queue depth

## Load Testing

See `load-tests/k6/scenario.js` for the k6 test script.

### How to run

```bash
# Install k6: https://k6.io/docs/getting-started/installation/
k6 run load-tests/k6/scenario.js

# With custom base URL
BASE_URL=http://production.example.com k6 run load-tests/k6/scenario.js

# With more load
k6 run --vus 20 --duration 60s load-tests/k6/scenario.js
```

### Current baseline (local dev)

Measured on: Hetzner CX22 (2 vCPU, 4GB RAM) — *to be filled after first run*

| Endpoint | p50 | p95 | p99 | Error rate |
|----------|-----|-----|-----|------------|
| `/health` | — | — | — | — |
| `/api/v1/suppliers` | — | — | — | — |
| `/api/v1/products` | — | — | — | — |
| `/api/v1/review-queue` | — | — | — | — |

## Monitoring

### Prometheus metrics available

- `http_request_count{method, endpoint, http_status}` — request volume
- `http_request_latency_seconds{method, endpoint}` — latency
- `db_query_count{query_type, table}` — database load
- `background_job_count{job_type, status}` — Celery job stats

### Key dashboards to build

1. **API Overview** — request rate, latency, error rate
2. **Database** — active connections, cache hit ratio, slow queries
3. **Queue** — Celery queue depth, processing time, failure rate
4. **Audit** — event volume by type (compliance)

---

*Last updated: 2026‑06‑18*
