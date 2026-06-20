# 04 — End-to-End Workflow (Step-by-step)

## 4.1 Στόχος
Ο παρακάτω ορισμός είναι ο “κανόνας” του προϊόντος: τι ακριβώς συμβαίνει από upload μέχρι export.

## 4.2 Κύριος βρόχος (happy path)

### Βήμα 1 — Supplier Setup
1. Δημιουργία supplier.
2. (Optional) Εμπλουτισμός supplier (AADE tax info, contacts).
3. Καταχώριση supplier-specific rules (π.χ. normalization κωδικών).

Έξοδος:
- Supplier record.
- Rule set version 1.

### Βήμα 2 — Upload εισόδου
Ο χρήστης ανεβάζει αρχείο (PDF/XML/Excel/img).

Καταγράφουμε:
- `inbound_file_id`
- sha256
- storage key
- uploader

Δημιουργείται job: `parse_document(inbound_file_id)`

### Βήμα 3 — Parse / Extract
Pipeline (deterministic-first):

1. **File-type detection**
2. Αν XML: parse structured fields.
3. Αν PDF:
   - table extraction (camelot/tabula) όταν είναι native
   - OCR όταν είναι scan/εικόνα
4. Αν εικόνα: OCR

Παράγονται:
- `parsed_document` + `line_items[]`
- status: success / needs_review / failed

### Βήμα 4 — Normalize
Για κάθε line item:
- normalize SKU/κωδικό με supplier rules
- normalize units/decimals

Παράδειγμα (Poimenidis):
- `03-XXXX` → `XXXX`

### Βήμα 5 — Matching
Για κάθε normalized SKU:

1. Exact lookup σε `ProductSupplierLink` για `(supplier_id, supplier_sku_normalized)`.
   - αν βρεθεί → auto_exact match

2. Αν όχι, generate candidates:
   - fuzzy στον normalized SKU
   - similarity στην περιγραφή (optional)
   - ιστορικό προηγούμενων matches

3. Αν confidence >= threshold → auto_suggested + ανοίγει ReviewTask
4. Αν confidence χαμηλό → ReviewTask υποχρεωτικό

> Lock: matching identity βασίζεται σε supplier/manufacturer κωδικούς, όχι σε Pylon codes.

### Βήμα 6 — Product create/update
- Αν item δεν matchάρει σε υπάρχον προϊόν:
  - δημιουργία provisional Product
  - δημιουργία ProductSupplierLink
  - άνοιγμα ReviewTask για enrichment

### Βήμα 7 — Enrichment (με ιεράρχηση)
Με αυστηρό precedence:

1. structured sources (XML/Excel list)
2. user-uploaded catalogs/product lists
3. manual
4. scraping last

Κάθε αλλαγή γράφει EnrichmentEvent + provenance.

### Βήμα 8 — Human Review
Review queue UI:
- βλέπει extracted fields + source preview
- αποδέχεται/διορθώνει
- κλείνει tasks

### Βήμα 9 — Export
- Ο χρήστης επιλέγει export type (μορφή συμφωνημένη).
- Validation: υποχρεωτικά πεδία, decimals, κενά.
- Παραγωγή αρχείου στο MinIO + download link.

## 4.3 Error paths
### Parse failure
- status failed
- ReviewTask: “parse_fix”
- UI δείχνει raw file + extracted fragments

### Ambiguous match
- ReviewTask: “match_confirm”
- UI δείχνει candidates + rationale

### Conflicting enrichment
- Rule: δεν overwrite manual χωρίς explicit user action
- ReviewTask: “enrichment_confirm”

## 4.4 Audit & traceability
Για κάθε document:
- timeline events
- who approved
- what changed
- export version
