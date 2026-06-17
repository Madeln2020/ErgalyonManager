# 08 — Review Queue & UI

## 8.1 Στόχος
Η εφαρμογή πρέπει να είναι usable ως “εργαλείο παραγωγής” και όχι demo.
Το review queue είναι ο πυρήνας της αξιοπιστίας.

## 8.2 Τύποι tasks
- `parse_fix`: διόρθωση extraction/πίνακα
- `match_confirm`: επιβεβαίωση/αλλαγή matching
- `enrichment_confirm`: επιβεβαίωση specs/κατηγοριών
- `export_validate`: validation πριν export

## 8.3 UI screens (minimum)
### 8.3.1 Supplier page
- supplier info
- rules version
- documents (agreements/catalogs)

### 8.3.2 Upload page
- drag&drop
- select supplier
- show detected type
- submit → job created

### 8.3.3 Document review page
- preview of PDF/XML
- extracted header fields
- line items table (editable)
- highlight low-confidence cells

### 8.3.4 Matching review
- for each line item:
  - chosen product
  - candidate list with scores
  - actions: accept candidate, search manually, create new

### 8.3.5 Product page
- canonical data
- supplier links
- history
- enrichment suggestions

### 8.3.6 Review queue inbox
- filters by supplier, type, status
- bulk actions

## 8.4 Bulk edit behaviors
- bulk accept matches above threshold
- bulk apply normalization rule update (with re-run)

## 8.5 Guardrails
- destructive actions require confirmation
- show provenance next to fields

## 8.6 Audit
- every approval logs: user, timestamp, before/after

## 8.7 UX details (recommended)
- keyboard shortcuts for approve/next
- diff view for enrichment (field-level)
- “why” panel for AI suggestions
