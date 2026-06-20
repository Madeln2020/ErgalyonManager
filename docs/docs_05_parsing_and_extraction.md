# 05 — Parsing & Extraction

## 5.1 Design principle
**Extraction is not truth.** Είναι μια πρόταση δεδομένων με confidence + provenance.

## 5.2 Input types
- XML: structured, υψηλή αξιοπιστία.
- PDF native: table extraction.
- PDF scan / images: OCR.
- Excel: structured lists/price lists.

## 5.3 Extraction layers (fallback chain)
### Layer A — Deterministic structured parsing
- XML parser: schema-aware (αν υπάρχει) ή rule-based.
- Excel parser: columns mapping per supplier.

### Layer B — Table extraction from PDFs
- Camelot/Tabula για πίνακες.
- Heuristics: detect header row, columns, currency, decimals.

### Layer C — OCR
- Preprocess image (deskew, contrast).
- OCR engine.
- Layout analysis (line segmentation).

### Layer D — AI-assisted extraction
Χρησιμοποιείται όταν:
- η δομή δεν είναι σταθερή,
- table extraction αποτυγχάνει,
- OCR βγάζει θόρυβο.

AI πρέπει να επιστρέφει **structured JSON** με schema και να δίνει rationale.

## 5.4 Output schema (canonical)
Η εφαρμογή πρέπει να παράγει canonical μορφή για κάθε line item:
- `sku_raw`
- `sku_normalized`
- `description`
- `qty`
- `unit_price`
- `line_total`
- `vat_rate` (αν υπάρχει)
- `source` (xml/pdf_table/pdf_ocr/manual)
- `confidence` (0..1)

## 5.5 Validation rules
- qty > 0
- unit_price >= 0
- line_total ~ qty*unit_price (με tolerance)
- decimals: normalize ελληνικά format (comma vs dot)

## 5.6 Supplier-specific templates
Για suppliers με “σωστή δομή”:
- κρατάμε template definition (columns, regex, positions).
- versioned template.

## 5.7 Storage of artifacts
Στο MinIO:
- raw file
- extracted text
- extracted tables (CSV/JSON)
- OCR images

Στη DB:
- references (object keys)
- parse metadata

## 5.8 Review triggers
Ανοίγουμε ReviewTask όταν:
- parse confidence κάτω από threshold
- totals mismatch
- missing sku
- too many unknown items

## 5.9 Determinism vs AI
Ό,τι είναι 100% deterministic (π.χ. regex extraction) να γίνεται πριν από AI.
AI να είναι fallback και να μην αλλάζει raw data.
