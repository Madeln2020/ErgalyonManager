# 03 — Data Model (Proposed)

> Αυτό είναι προτεινόμενο σχήμα. Ο χρήστης δεν δεσμεύεται από συγκεκριμένη δομή, αρκεί να καλύπτει το σκοπό.

## 3.1 Design goals
- Καλύπτει end-to-end: uploads → parsed docs → items → matching → product DB → enrichment → export.
- Κρατάει provenance & history.
- Επιτρέπει supplier-specific rules.

## 3.2 Core entities

### 3.2.1 Supplier
Στόχος: όλα τα supplier metadata, κανόνες, έγγραφα.

Ενδεικτικά πεδία:
- `id` (UUID)
- `name`
- `vat_number` (ΑΦΜ) (προσοχή privacy)
- `tax_profile_json` (AADE enriched fields)
- `contacts_json`
- `default_currency`
- `created_at`, `updated_at`

### 3.2.2 SupplierDocument (Agreement/Catalog/etc)
- `id` (UUID)
- `supplier_id`
- `doc_type` (agreement, catalog, price_list, other)
- `object_key` (MinIO)
- `title`
- `extracted_text_object_key`
- `embedding_ref` (αν υπάρχει)
- `created_at`

### 3.2.3 InboundFile (upload)
- `id`
- `supplier_id` (nullable αν δεν έχει επιλεγεί ακόμα)
- `file_type` (pdf/xml/xlsx/img)
- `object_key`
- `sha256`
- `uploaded_by`
- `uploaded_at`

### 3.2.4 ParsedDocument
Αντιπροσωπεύει το αποτέλεσμα extraction.

- `id`
- `inbound_file_id`
- `doc_kind` (invoice/offer/catalog/unknown)
- `parse_status` (pending/success/needs_review/failed)
- `parser_version`
- `confidence_score` (προαιρετικό)
- `header_json` (date, doc_number, totals)
- `created_at`

### 3.2.5 ParsedLineItem
- `id`
- `parsed_document_id`
- `line_index`
- `supplier_sku_raw`
- `supplier_sku_normalized`
- `description_raw`
- `qty`
- `unit_price`
- `line_total`
- `vat_rate`
- `extraction_source` (xml/pdf_ocr/pdf_table/manual/vision/llm)
- `extraction_notes`

### 3.2.6 Product
Κεντρικό προϊόν στο EDM.

- `id`
- `canonical_name`
- `internal_code` (optional)
- `technical_specs_json`
- `category_path` (ή FK σε categories)
- `status` (active/provisional/archived)
- `created_at`

### 3.2.7 ProductSupplierLink
Το κλειδί της ταυτοποίησης.

- `id`
- `product_id`
- `supplier_id`
- `supplier_sku_normalized` (unique per supplier)
- `supplier_sku_raw_examples` (array)
- `last_seen_at`
- `price_history_json` (ή normalized table)

### 3.2.8 MatchDecision
Καταγράφει την απόφαση matching (manual ή auto).

- `id`
- `parsed_line_item_id`
- `product_id` (nullable αν create-new)
- `decision_type` (auto_exact/auto_suggested/manual_confirm/manual_override)
- `candidates_json` (top candidates + scores)
- `decided_by`
- `decided_at`

### 3.2.9 EnrichmentEvent
Κάθε enrichment action.

- `id`
- `product_id`
- `source_type` (xml/list/catalog/manual/scrape)
- `source_ref` (file_id/url)
- `changes_json` (diff)
- `applied_by`
- `applied_at`

### 3.2.10 ReviewTask
Μοντελοποιεί την ουρά.

- `id`
- `task_type` (parse_fix/match_confirm/enrichment_confirm/export_validate)
- `entity_ref` (parsed_document_id / line_item_id / product_id)
- `status` (open/in_progress/done)
- `assigned_to` (nullable)
- `created_at`, `closed_at`

## 3.3 Provenance strategy
Για κάθε σημαντικό πεδίο, πρέπει να ξέρουμε:
- από ποια πηγή ήρθε,
- πότε,
- από ποιον,
- αν είναι overwriteable.

Πρακτική υλοποίηση:
- είτε per-field provenance map (JSONB)
- είτε per-change log (EnrichmentEvent + audit log)

## 3.4 Migrations & versioning
- Migrations με Alembic.
- Versioning του parser (`parser_version`) για reproducibility.
