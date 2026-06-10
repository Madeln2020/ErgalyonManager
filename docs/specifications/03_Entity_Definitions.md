## 3. Entity Definitions

### 3.1 Product

**Κεντρική οντότητα του συστήματος**. Αντιπροσωπεύει ένα εργαλείο/προϊόν.

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `ergalyon_code` | VARCHAR(50) | Yes | Κωδικός Εργαλύων - Auto-generated, unique, format: ERG-XXXXXXXX |
| `supplier_code` | VARCHAR(100) | Yes | Κωδικός Προμηθευτή - REQUIRED, used for lookups |
| `manufacturer_code` | VARCHAR(100) | No | Κωδικός Κατασκευαστή - Optional, enriched |
| `supplier_id` | UUID | Yes | Foreign key to Supplier |
| `manufacturer_id` | UUID | No | Foreign key to Manufacturer (optional) |
| `description` | TEXT | Yes | Product description (from invoice) |
| `description_normalized` | TEXT | Yes | Cleaned/normalized description for search |
| `category_k1_id` | UUID | No | Category Level 1 |
| `category_k2_id` | UUID | No | Category Level 2 |
| `category_k3_id` | UUID | No | Category Level 3 |
| `category_confidence` | DECIMAL(5,2) | No | ML confidence score (0-100) |
| `current_price` | DECIMAL(10,2) | No | Latest price |
| `price_currency` | VARCHAR(3) | No | EUR, USD, etc. |
| `image_url` | TEXT | No | Product image (from catalog or scraped) |
| `barcode` | VARCHAR(50) | No | EAN/UPC if available |
| `manufacturer_flag` | BOOLEAN | No | Flag: "Supplier code might be manufacturer code" |
| `data_completeness_score` | INTEGER | No | 0-100, how complete is the data |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |
| `updated_at` | TIMESTAMP | Yes | Last update timestamp |
| `created_by` | UUID | No | User who created (NULL if auto) |
| `updated_by` | UUID | No | User who last updated |

#### Indexes & Constraints (Product)
- `UNIQUE(ergalyon_code)` — global uniqueness
- `UNIQUE(supplier_id, supplier_code)` — ένας supplier code ανά προμηθευτή
- `INDEX(description_normalized)` — full-text search
- `INDEX(category_k1_id, category_k2_id, category_k3_id)` — category filtering

---

### 3.2 Supplier

Αντιπροσωπεύει έναν προμηθευτή εργαλείων.

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `name` | VARCHAR(255) | Yes | Επωνυμία προμηθευτή |
| `vat_number` | VARCHAR(20) | No | ΑΦΜ |
| `country` | VARCHAR(2) | No | ISO country code (default: GR) |
| `contact_email` | VARCHAR(255) | No | Email επικοινωνίας |
| `contact_phone` | VARCHAR(50) | No | Τηλέφωνο |
| `rules_json` | JSONB | No | Supplier-specific rules (βλ. §8) |
| `default_category_k1_id` | UUID | No | Default κατηγορία αν ο supplier είναι single-category |
| `parsing_profile` | VARCHAR(50) | No | Προτεινόμενος parser (xml/pdf_structured/ocr) |
| `is_active` | BOOLEAN | Yes | Ενεργός προμηθευτής (default: true) |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |
| `updated_at` | TIMESTAMP | Yes | Last update timestamp |

**Note:** Το `rules_json` περιέχει το πλήρες rule set που εφαρμόζει το Supplier Rule Engine (§8). Παράδειγμα Poimenidis: `{"code_normalization": [{"type": "strip_prefix", "prefix": "03-"}]}`.

---

### 3.3 Invoice

Header οντότητα τιμολογίου/προσφοράς.

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `supplier_id` | UUID | Yes | Foreign key to Supplier |
| `document_type` | VARCHAR(20) | Yes | invoice / offer / catalog |
| `invoice_number` | VARCHAR(100) | No | Αριθμός παραστατικού |
| `invoice_date` | DATE | No | Ημερομηνία παραστατικού |
| `file_path` | TEXT | Yes | Path του original αρχείου (storage) |
| `file_format` | VARCHAR(20) | Yes | xml / pdf / image / excel |
| `status` | VARCHAR(30) | Yes | Lifecycle status (βλ. §4.1) |
| `parsed_data_json` | JSONB | No | Raw parsed output πριν normalization |
| `parsing_confidence` | DECIMAL(5,2) | No | Overall confidence (0-100) |
| `total_amount` | DECIMAL(12,2) | No | Συνολικό ποσό |
| `currency` | VARCHAR(3) | No | EUR, USD, etc. |
| `error_message` | TEXT | No | Μήνυμα σφάλματος αν status=failed |
| `created_at` | TIMESTAMP | Yes | Upload timestamp |
| `processed_at` | TIMESTAMP | No | Ολοκλήρωση processing |

**Status values:** `uploaded → parsing → parsed → normalized → enriched → reviewed → exported` (βλ. §4.2 για state transitions). Επιπλέον: `failed`.

---

### 3.4 InvoiceItem

Γραμμή τιμολογίου — συνδέει το Invoice με ένα Product.

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `invoice_id` | UUID | Yes | Foreign key to Invoice |
| `product_id` | UUID | No | Foreign key to Product (NULL μέχρι το matching) |
| `line_number` | INTEGER | No | Σειρά στη γραμμή τιμολογίου |
| `raw_supplier_code` | VARCHAR(100) | No | Κωδικός όπως εμφανίζεται πριν normalization |
| `normalized_supplier_code` | VARCHAR(100) | No | Μετά την εφαρμογή των rules |
| `raw_description` | TEXT | Yes | Περιγραφή από το παραστατικό |
| `quantity` | DECIMAL(10,3) | No | Ποσότητα |
| `unit_price` | DECIMAL(10,2) | No | Τιμή μονάδας |
| `line_total` | DECIMAL(12,2) | No | Σύνολο γραμμής |
| `vat_rate` | DECIMAL(5,2) | No | Συντελεστής ΦΠΑ |
| `match_confidence` | DECIMAL(5,2) | No | Confidence του product matching |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |

---

### 3.5 SupplierAgreement

Συμφωνητικό προμηθευτή — αποθηκεύεται **μόνο για RAG/Archive**, ΟΧΙ για validation/comparison (βλ. Out of Scope).

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `supplier_id` | UUID | Yes | Foreign key to Supplier |
| `title` | VARCHAR(255) | No | Τίτλος/περιγραφή συμφωνητικού |
| `file_path` | TEXT | Yes | Path του original εγγράφου |
| `valid_from` | DATE | No | Έναρξη ισχύος |
| `valid_to` | DATE | No | Λήξη ισχύος |
| `rag_index_id` | VARCHAR(100) | No | Reference στο vector store (chunk collection) |
| `indexed_at` | TIMESTAMP | No | Πότε έγινε το RAG indexing |
| `created_at` | TIMESTAMP | Yes | Upload timestamp |

**Note:** Το EDM **δεν** συγκρίνει τα συμφωνητικά με τα τιμολόγια. Χρησιμοποιούνται αποκλειστικά για semantic search (π.χ. «ποια ήταν η συμφωνημένη έκπτωση;»).

---

### 3.6 Category

3-level ιεραρχία κατηγοριών (K1/K2/K3).

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `level` | INTEGER | Yes | 1, 2, ή 3 |
| `name` | VARCHAR(255) | Yes | Όνομα κατηγορίας (π.χ. "Πριόνια") |
| `parent_id` | UUID | No | Foreign key to Category (NULL για level 1) |
| `code` | VARCHAR(50) | No | Internal category code |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |

**Constraint:** `parent_id` πρέπει να δείχνει σε κατηγορία ένα επίπεδο πάνω (level N → level N-1). Level 1 έχει `parent_id = NULL`.

---

### 3.7 ProductSpecification

Technical specs ως flexible key-value pairs.

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `product_id` | UUID | Yes | Foreign key to Product |
| `spec_key` | VARCHAR(100) | Yes | π.χ. "Ισχύς", "Βάρος", "Τάση" |
| `spec_value` | VARCHAR(255) | Yes | π.χ. "800W", "2.5kg", "220V" |
| `unit` | VARCHAR(20) | No | Μονάδα μέτρησης |
| `source` | VARCHAR(20) | Yes | xml / catalog / manual / scraping |
| `source_confidence` | DECIMAL(5,2) | No | Confidence της εξαγωγής |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |

**Constraint:** `UNIQUE(product_id, spec_key)` — μία τιμή ανά spec key (η νεότερη/υψηλότερης προτεραιότητας πηγή υπερισχύει).

---

### 3.8 ReviewQueueItem

Item που χρειάζεται human review (βλ. §7 για πλήρη specification).

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `product_id` | UUID | No | Foreign key to Product (αν αφορά προϊόν) |
| `invoice_item_id` | UUID | No | Foreign key to InvoiceItem (αν αφορά γραμμή) |
| `review_type` | VARCHAR(50) | Yes | low_confidence / duplicate / missing_manufacturer_code / price_anomaly / new_supplier |
| `priority` | VARCHAR(20) | Yes | CRITICAL / HIGH / MEDIUM / LOW |
| `status` | VARCHAR(20) | Yes | open / in_progress / resolved / dismissed |
| `payload_json` | JSONB | No | Context data (suggested values, confidence scores) |
| `prompt_text` | TEXT | No | Ερώτηση προς τον χρήστη |
| `resolution` | VARCHAR(50) | No | approved / edited / rejected |
| `resolved_by` | UUID | No | User που έλυσε το item |
| `resolved_at` | TIMESTAMP | No | Χρόνος επίλυσης |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |


---
