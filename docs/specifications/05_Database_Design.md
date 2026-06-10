## 5. Database Design

### 5.1 Schema Overview

Η βάση δεδομένων είναι **PostgreSQL 15+**. Χρησιμοποιεί `UUID` primary keys (`gen_random_uuid()`), `JSONB` για flexible/semi-structured data, και `TIMESTAMPTZ` για όλα τα timestamps.

```
┌─────────────────────────────────────────────────────────────────┐
│                    EDM DATABASE SCHEMA (overview)                │
└─────────────────────────────────────────────────────────────────┘

  suppliers ──1:N──┬── supplier_rules
                   ├── supplier_agreements
                   └── invoices ──1:N── invoice_items ──N:1── products
                                                                  │
  categories (self-ref K1/K2/K3) ──┐                             │
                                    └──N:1────────────────────────┤
                                                                  ├── product_specifications
                                                                  ├── product_source_data
                                                                  ├── price_history
                                                                  └── review_queue
```

**Extensions:**
```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- trigram search σε descriptions
CREATE EXTENSION IF NOT EXISTS "vector";      -- (προαιρετικό) RAG embeddings
```

### 5.2 Table Definitions

#### 5.2.1 suppliers

```sql
CREATE TABLE suppliers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    VARCHAR(255) NOT NULL,
    vat_number              VARCHAR(20),
    country                 VARCHAR(2) NOT NULL DEFAULT 'GR',
    contact_email           VARCHAR(255),
    contact_phone           VARCHAR(50),
    rules_json              JSONB NOT NULL DEFAULT '{}'::jsonb,
    default_category_k1_id  UUID REFERENCES categories(id),
    parsing_profile         VARCHAR(50),
    is_active               BOOLEAN NOT NULL DEFAULT true,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_supplier_vat UNIQUE (vat_number)
);
```

#### 5.2.2 categories

```sql
CREATE TABLE categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level       SMALLINT NOT NULL CHECK (level IN (1, 2, 3)),
    name        VARCHAR(255) NOT NULL,
    parent_id   UUID REFERENCES categories(id) ON DELETE RESTRICT,
    code        VARCHAR(50),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_level1_no_parent
        CHECK ((level = 1 AND parent_id IS NULL) OR (level > 1 AND parent_id IS NOT NULL))
);
```

#### 5.2.3 products

```sql
CREATE TABLE products (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ergalyon_code            VARCHAR(50) NOT NULL,
    supplier_code            VARCHAR(100) NOT NULL,
    manufacturer_code        VARCHAR(100),
    ean                      VARCHAR(50),
    supplier_id              UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    manufacturer_id          UUID,
    description              TEXT NOT NULL,
    description_normalized   TEXT NOT NULL,
    specs_json               JSONB NOT NULL DEFAULT '{}'::jsonb,
    category_k1_id           UUID REFERENCES categories(id),
    category_k2_id           UUID REFERENCES categories(id),
    category_k3_id           UUID REFERENCES categories(id),
    category_confidence      DECIMAL(5,2),
    current_price            DECIMAL(10,2),
    price_currency           VARCHAR(3),
    image_url                TEXT,
    manufacturer_flag        BOOLEAN NOT NULL DEFAULT false,
    data_completeness_score  SMALLINT CHECK (data_completeness_score BETWEEN 0 AND 100),
    is_deleted               BOOLEAN NOT NULL DEFAULT false,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by               UUID,
    updated_by               UUID,
    CONSTRAINT uq_ergalyon_code UNIQUE (ergalyon_code),
    CONSTRAINT uq_supplier_code UNIQUE (supplier_id, supplier_code)
);
```

> **Note:** Το `specs_json` κρατά ένα denormalized snapshot των specs για γρήγορα reads· η κανονική (normalized) πηγή αλήθειας είναι ο πίνακας `product_specifications`.

#### 5.2.4 invoices

```sql
CREATE TABLE invoices (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id         UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    document_type       VARCHAR(20) NOT NULL DEFAULT 'invoice'
                          CHECK (document_type IN ('invoice','offer','catalog')),
    invoice_number      VARCHAR(100),
    invoice_date        DATE,
    file_path           TEXT NOT NULL,
    file_format         VARCHAR(20) NOT NULL
                          CHECK (file_format IN ('xml','pdf','image','excel')),
    status              VARCHAR(30) NOT NULL DEFAULT 'uploaded'
                          CHECK (status IN ('uploaded','parsing','parsed','normalized',
                                            'enriched','reviewed','exported','failed')),
    parsed_data_json    JSONB,
    parsing_confidence  DECIMAL(5,2),
    total_amount        DECIMAL(12,2),
    currency            VARCHAR(3) DEFAULT 'EUR',
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at        TIMESTAMPTZ
);
```

#### 5.2.5 invoice_items

```sql
CREATE TABLE invoice_items (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id                UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id                UUID REFERENCES products(id) ON DELETE SET NULL,
    line_number               INTEGER,
    raw_supplier_code         VARCHAR(100),
    normalized_supplier_code  VARCHAR(100),
    raw_description           TEXT NOT NULL,
    quantity                  DECIMAL(10,3),
    unit_price                DECIMAL(10,2),
    line_total                DECIMAL(12,2),
    vat_rate                  DECIMAL(5,2),
    match_confidence          DECIMAL(5,2),
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 5.2.6 product_source_data

Παρακολούθηση data precedence (XML > Catalog > Manual > Scraping) ανά πεδίο.

```sql
CREATE TABLE product_source_data (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id        UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    field_name        VARCHAR(100) NOT NULL,
    field_value       TEXT,
    source            VARCHAR(20) NOT NULL
                        CHECK (source IN ('xml','catalog','manual','scraping')),
    source_priority   SMALLINT NOT NULL,   -- 1=manual, 2=xml, 3=catalog, 4=scraping
    source_ref        TEXT,                -- invoice_id ή URL
    confidence        DECIMAL(5,2),
    is_active         BOOLEAN NOT NULL DEFAULT true,  -- η τρέχουσα winning value
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_active_field
        EXCLUDE (product_id WITH =, field_name WITH =) WHERE (is_active)
);
```

> Το `EXCLUDE` constraint εγγυάται ότι υπάρχει το πολύ **μία active value** ανά (product, field). Όταν έρχεται νέα τιμή υψηλότερης προτεραιότητας, η παλιά γίνεται `is_active=false` (διατήρηση ιστορικού — RULE U1/U2).

#### 5.2.7 product_specifications

```sql
CREATE TABLE product_specifications (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id         UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    spec_key           VARCHAR(100) NOT NULL,
    spec_value         VARCHAR(255) NOT NULL,
    unit               VARCHAR(20),
    source             VARCHAR(20) NOT NULL
                         CHECK (source IN ('xml','catalog','manual','scraping')),
    source_confidence  DECIMAL(5,2),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_product_spec UNIQUE (product_id, spec_key)
);
```

#### 5.2.8 price_history

```sql
CREATE TABLE price_history (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id   UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price        DECIMAL(10,2) NOT NULL,
    currency     VARCHAR(3) NOT NULL DEFAULT 'EUR',
    supplier_id  UUID REFERENCES suppliers(id),
    invoice_id   UUID REFERENCES invoices(id),
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 5.2.9 supplier_rules

> Οι κανόνες αποθηκεύονται **και** ως κανονικοποιημένος πίνακας (audit/versioning) **και** denormalized στο `suppliers.rules_json` για γρήγορη φόρτωση από το engine.

```sql
CREATE TABLE supplier_rules (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id  UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    rule_type    VARCHAR(50) NOT NULL
                   CHECK (rule_type IN ('code_normalization','field_mapping',
                                        'validation','enrichment_hint')),
    config_json  JSONB NOT NULL,
    priority     SMALLINT NOT NULL DEFAULT 100,  -- χαμηλότερο = πρώτο
    is_active    BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 5.2.10 supplier_agreements

```sql
CREATE TABLE supplier_agreements (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id   UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    title         VARCHAR(255),
    file_path     TEXT NOT NULL,
    valid_from    DATE,
    valid_to      DATE,
    rag_index_id  VARCHAR(100),
    indexed_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 5.2.11 review_queue

```sql
CREATE TABLE review_queue (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id       UUID REFERENCES products(id) ON DELETE CASCADE,
    invoice_item_id  UUID REFERENCES invoice_items(id) ON DELETE CASCADE,
    review_type      VARCHAR(50) NOT NULL
                       CHECK (review_type IN ('low_confidence','duplicate',
                              'missing_manufacturer_code','price_anomaly','new_supplier')),
    priority         VARCHAR(20) NOT NULL
                       CHECK (priority IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    status           VARCHAR(20) NOT NULL DEFAULT 'open'
                       CHECK (status IN ('open','in_progress','resolved','dismissed')),
    payload_json     JSONB,
    prompt_text      TEXT,
    resolution       VARCHAR(50) CHECK (resolution IN ('approved','edited','rejected')),
    resolved_by      UUID,
    resolved_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 5.2.12 audit_log

```sql
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id   UUID NOT NULL,
    event_name  VARCHAR(100) NOT NULL,
    payload     JSONB,
    user_id     UUID,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 5.3 Indexes

```sql
-- Products: γρήγορα lookups & search
CREATE INDEX idx_products_supplier        ON products(supplier_id);
CREATE INDEX idx_products_supplier_code   ON products(supplier_id, supplier_code);
CREATE INDEX idx_products_manufacturer    ON products(manufacturer_code);
CREATE INDEX idx_products_ean             ON products(ean);
CREATE INDEX idx_products_categories      ON products(category_k1_id, category_k2_id, category_k3_id);
CREATE INDEX idx_products_desc_trgm       ON products USING gin (description_normalized gin_trgm_ops);
CREATE INDEX idx_products_specs_gin       ON products USING gin (specs_json);

-- Invoices & items
CREATE INDEX idx_invoices_supplier_status ON invoices(supplier_id, status);
CREATE INDEX idx_invoice_items_invoice    ON invoice_items(invoice_id);
CREATE INDEX idx_invoice_items_product    ON invoice_items(product_id);

-- Review queue: dashboard queries (open items by priority)
CREATE INDEX idx_review_open_priority     ON review_queue(status, priority)
    WHERE status IN ('open','in_progress');

-- Price history
CREATE INDEX idx_price_history_product    ON price_history(product_id, recorded_at DESC);

-- Source data precedence
CREATE INDEX idx_source_active            ON product_source_data(product_id, field_name)
    WHERE is_active;
```

### 5.4 Constraints

**Foreign Keys & Referential Integrity (σύνοψη):**

| Child | Parent | On Delete | Σημείωση |
|-------|--------|-----------|----------|
| `products.supplier_id` | `suppliers.id` | RESTRICT | Δεν διαγράφεται supplier με προϊόντα |
| `products.category_kN_id` | `categories.id` | (default) | 3 ξεχωριστά FK |
| `invoices.supplier_id` | `suppliers.id` | RESTRICT | |
| `invoice_items.invoice_id` | `invoices.id` | CASCADE | Διαγραφή invoice → items |
| `invoice_items.product_id` | `products.id` | SET NULL | Διατήρηση γραμμής |
| `product_source_data.product_id` | `products.id` | CASCADE | |
| `product_specifications.product_id` | `products.id` | CASCADE | |
| `price_history.product_id` | `products.id` | CASCADE | |
| `review_queue.product_id` | `products.id` | CASCADE | |
| `supplier_rules.supplier_id` | `suppliers.id` | CASCADE | |
| `supplier_agreements.supplier_id` | `suppliers.id` | CASCADE | |
| `categories.parent_id` | `categories.id` | RESTRICT | Δενδρική ιεραρχία |

**Business constraints (enforced):**
- `UNIQUE(ergalyon_code)` — global
- `UNIQUE(supplier_id, supplier_code)` — ένας κωδικός ανά προμηθευτή (RULE P1)
- `UNIQUE(product_id, spec_key)` — μία spec value ανά key
- `EXCLUDE` σε `product_source_data` — μία active value ανά (product, field)
- `CHECK` σε όλα τα status/enum πεδία
- Soft delete μέσω `products.is_deleted` (RULE — audit trail)


---
