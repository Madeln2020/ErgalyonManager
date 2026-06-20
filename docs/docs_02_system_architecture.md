# 02 — System Architecture

## 2.1 High level
Το EDM v2 προτείνεται να χωρίζεται σε 5 βασικά υποσυστήματα:

1) **Web App / API (FastAPI)**
- UI + REST endpoints
- auth/RBAC
- orchestrates workflows (create jobs)

2) **Core Data Store (PostgreSQL)**
- transactional storage
- history/provenance
- optional: `pgvector` για embeddings

3) **Object Storage (MinIO S3-compatible)**
- raw uploads (PDF/XML/Excel/images)
- derived artifacts (OCR text, extracted tables, screenshots, scraped html)

4) **Job Queue (Redis + worker)**
- background tasks: parsing, OCR, enrichment, scraping

5) **AI Orchestration Layer (Hermes Agent)**
- policy based routing: local vs remote
- abstraction layer για LLM calls
- logging/metrics per request

## 2.2 Why Hermes
Hermes υπάρχει για να λύσει 3 προβλήματα:

- **Δεδομένα**: τι μένει local και τι βγαίνει έξω.
- **Αξιοπιστία**: fallbacks (local → freeLLMAPI → Abacus) με κανόνες.
- **Κόστος/latency**: routing ανά task.

Hermes δεν είναι “μαγικό AI”. Είναι **router/orchestrator** με deterministic policies.

## 2.3 Proposed services (logical)
- `api` (FastAPI): main app
- `worker` (Celery/RQ/Custom): background pipeline
- `hermes` (FastAPI): model routing + eval hooks
- `postgres` (+vector)
- `redis`
- `minio`

> Αν θέλετε, `hermes` μπορεί αρχικά να είναι library module μέσα στο `api` για MVP, και μετά να γίνει ξεχωριστό service.

## 2.4 Environments
- **local**: docker-compose, dummy secrets
- **staging**: ίδια σύνθεση με production, αλλά περιορισμένα δεδομένα
- **prod**: hardened TLS, backups, monitoring

## 2.5 Deployment
- Container-based deployment σε Hetzner.
- Reverse proxy (Traefik/Nginx).
- TLS via Let's Encrypt.

## 2.6 Observability
- Structured logging (JSON) σε όλα τα services.
- Metrics: parsing success rate, review rate, time-to-export.
- Tracing per document/job.

## 2.7 Key architectural invariants (πρέπει να τηρηθούν)
- Όλες οι διαδικασίες pipeline γράφουν **provenance**.
- Κανένα worker task δεν κάνει irreversible αλλαγές χωρίς:
  - explicit policy, ή
  - user approval (review).
