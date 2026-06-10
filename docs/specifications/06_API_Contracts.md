## 6. API Contracts

REST API υλοποιημένο με **FastAPI**. Base path: `/api/v1`. Content-Type: `application/json` (εκτός uploads → `multipart/form-data`). Authentication: Bearer JWT.

### 6.1 REST Endpoints

| Method | Path | Σκοπός |
|--------|------|--------|
| POST | `/suppliers` | Δημιουργία προμηθευτή |
| GET | `/suppliers` | Λίστα προμηθευτών |
| GET | `/suppliers/{id}` | Λεπτομέρειες προμηθευτή |
| PUT | `/suppliers/{id}` | Ενημέρωση προμηθευτή/rules |
| POST | `/suppliers/{id}/agreement` | Upload συμφωνητικού (RAG) |
| POST | `/invoices/upload` | Upload τιμολογίου/προσφοράς |
| GET | `/invoices/{id}` | Status & metadata τιμολογίου |
| GET | `/invoices/{id}/items` | Parsed γραμμές τιμολογίου |
| GET | `/products` | Search/list προϊόντων |
| GET | `/products/{id}` | Λεπτομέρειες προϊόντος |
| PUT | `/products/{id}` | Ενημέρωση προϊόντος (manual override) |
| POST | `/products/{id}/enrich` | Trigger enrichment/scraping |
| GET | `/review-queue` | Items προς review |
| POST | `/review-queue/{id}/resolve` | Επίλυση review item |
| GET | `/export` | Export δεδομένων |

### 6.2 Request/Response Formats

#### POST /suppliers
```http
POST /api/v1/suppliers
Content-Type: application/json

{
  "name": "Ποιμενίδης Α.Ε.",
  "vat_number": "094xxxxxx",
  "country": "GR",
  "parsing_profile": "xml",
  "rules_json": {
    "code_normalization": [{ "type": "strip_prefix", "prefix": "03-" }]
  }
}
```
**201 Created**
```json
{ "id": "8f1c...", "name": "Ποιμενίδης Α.Ε.", "is_active": true, "created_at": "2026-06-10T10:00:00Z" }
```

#### POST /suppliers/{id}/agreement
```http
POST /api/v1/suppliers/8f1c.../agreement
Content-Type: multipart/form-data

file=<binary>, title="Συμφωνητικό 2026", valid_from=2026-01-01
```
**202 Accepted** — indexing async
```json
{ "id": "a2b3...", "supplier_id": "8f1c...", "status": "indexing", "rag_index_id": null }
```

#### POST /invoices/upload
```http
POST /api/v1/invoices/upload
Content-Type: multipart/form-data

supplier_id=8f1c..., document_type=invoice, files=<binary[]>
```
**202 Accepted**
```json
{
  "invoices": [
    { "id": "c4d5...", "file_format": "xml", "status": "uploaded" }
  ],
  "job_id": "job_77a1"
}
```

#### GET /invoices/{id}/items
**200 OK**
```json
{
  "invoice_id": "c4d5...",
  "status": "normalized",
  "items": [
    {
      "id": "e6f7...",
      "line_number": 1,
      "raw_supplier_code": "03-12345",
      "normalized_supplier_code": "12345",
      "raw_description": "ΣΕΓΑ ΣΠΑΘΟΥ 800W",
      "quantity": 2,
      "unit_price": 89.90,
      "match_confidence": 92.5,
      "product_id": "p100..."
    }
  ]
}
```

#### PUT /products/{id}
Manual override — δημιουργεί `source=manual` (υψηλότερη προτεραιότητα, RULE P4).
```http
PUT /api/v1/products/p100...
Content-Type: application/json

{
  "manufacturer_code": "BOSCH-2607",
  "category_k1_id": "k1...", "category_k2_id": "k2...", "category_k3_id": "k3...",
  "specs": [{ "spec_key": "Ισχύς", "spec_value": "800", "unit": "W" }]
}
```
**200 OK** — επιστρέφει το ενημερωμένο product με `updated_at` & `data_completeness_score`.

#### GET /review-queue
Query params: `status`, `priority`, `review_type`, `limit`, `offset`.
```http
GET /api/v1/review-queue?status=open&priority=HIGH&limit=20
```
**200 OK**
```json
{
  "total": 42,
  "items": [
    {
      "id": "r1...",
      "review_type": "missing_manufacturer_code",
      "priority": "HIGH",
      "product_id": "p100...",
      "prompt_text": "Θα χρησιμοποιηθεί ο κωδικός προμηθευτή ως κωδικός κατασκευαστή;",
      "payload": { "supplier_code": "12345", "suggestions": [] }
    }
  ]
}
```

#### POST /review-queue/{id}/resolve
```http
POST /api/v1/review-queue/r1.../resolve
Content-Type: application/json

{
  "resolution": "edited",
  "data": { "use_supplier_code_as_manufacturer": true }
}
```
**200 OK**
```json
{ "id": "r1...", "status": "resolved", "resolution": "edited", "resolved_at": "2026-06-10T10:30:00Z" }
```

#### POST /products/{id}/enrich
```http
POST /api/v1/products/p100.../enrich
Content-Type: application/json

{ "sources": ["catalog", "scraping"], "force": false }
```
**202 Accepted**
```json
{ "product_id": "p100...", "job_id": "enr_55", "status": "queued" }
```

#### GET /export
Query params: `format` (csv|excel|json|xml), `supplier_id`, `category_k1_id`, `date_from`, `date_to`, `review_status`.
```http
GET /api/v1/export?format=csv&supplier_id=8f1c...&date_from=2026-01-01
```
**200 OK** — `Content-Type: text/csv` (attachment) ή για μεγάλα datasets **202** με `job_id` & download URL.

### 6.3 Error Handling

Όλα τα errors ακολουθούν ενιαία δομή (RFC 7807-style):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "supplier_code is required",
    "details": [{ "field": "supplier_code", "issue": "missing" }],
    "request_id": "req_abc123"
  }
}
```

| HTTP Status | Code | Πότε |
|-------------|------|------|
| 400 | `VALIDATION_ERROR` | Λανθασμένο/ελλιπές input |
| 401 | `UNAUTHORIZED` | Missing/invalid JWT |
| 403 | `FORBIDDEN` | Ανεπαρκή δικαιώματα |
| 404 | `NOT_FOUND` | Entity δεν βρέθηκε |
| 409 | `CONFLICT` | Duplicate (π.χ. `supplier_code` υπάρχει) |
| 422 | `UNPROCESSABLE` | Parse failed / business rule violation |
| 429 | `RATE_LIMITED` | Πάρα πολλά requests |
| 500 | `INTERNAL_ERROR` | Server error (logged με `request_id`) |
| 503 | `SERVICE_UNAVAILABLE` | Worker/queue down |

**Σημειώσεις:**
- Async endpoints (upload, enrich, export μεγάλων datasets) επιστρέφουν `202` + `job_id`. Polling μέσω `GET /jobs/{job_id}`.
- Rate limiting: 100 req/min ανά API key (configurable).
- Pagination: `limit`/`offset` με `total` count σε όλα τα list endpoints.


---
