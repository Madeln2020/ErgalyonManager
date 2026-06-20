# 07 — Enrichment Pipeline (Source Precedence Engine)

## 7.1 Lock: σειρά εμπλουτισμού
Η σειρά πηγών είναι **αυστηρή**:

1) **Structured supplier data** (XML / Excel product lists / official price lists)
2) **User-attached documents** (catalog PDFs, product lists) — ως δεύτερο κύμα enrichment
3) **Manual edits** από χρήστη
4) **Web scraping** (τελευταίο)

## 7.2 Βασικός κανόνας προστασίας
- Manual edits **δεν overwrite** από scraping χωρίς explicit user action.

## 7.3 Τι σημαίνει enrichment output
Enrichment ενημερώνει:
- `canonical_name`
- `technical_specs_json`
- `category`
- `attachments` (datasheet/pdf)
- `images` (αν/όταν ζητηθεί)

## 7.4 Data precedence engine
Προτεινόμενη λογική:

Για κάθε πεδίο `field`:
- κρατάμε `field_value`
- κρατάμε `field_source` (structured/catalog/manual/scrape)
- κρατάμε `field_updated_at`

Update rule:
- Αν νέα πηγή έχει **υψηλότερη προτεραιότητα** → επιτρέπεται overwrite
- Αν ίση προτεραιότητα → overwrite μόνο αν:
  - νεότερο timestamp *και* user approved
- Αν χαμηλότερη προτεραιότητα → ποτέ overwrite, μόνο suggestion

## 7.5 Structured imports
### 7.5.1 XML
- parse known fields
- map to product/spec schema

### 7.5.2 Excel lists
- mapping per supplier:
  - column `supplier_sku`
  - column `name`
  - columns specs

## 7.6 Catalog/document-based enrichment
- user ανεβάζει catalog PDF
- pipeline: text extract → sectioning → candidate product extraction
- output: suggested specs per product with provenance “catalog”
- always goes to review queue

## 7.7 Scraping (last resort)
Χρησιμοποιείται όταν:
- δεν υπάρχουν structured sources
- δεν υπάρχουν catalogs/lists
- manual δεν επαρκεί

Scrape policy:
- keep raw html snapshot
- store parsed fields with source “scrape”
- never auto-overwrite manual

## 7.8 Review tasks
- `enrichment_confirm` tasks generated when:
  - new specs found
  - conflicts detected

## 7.9 Example precedence table
| Source | Priority | Auto-apply? |
|---|---:|---|
| XML/Excel list | 100 | yes (with validation) |
| Catalog attach | 70 | no (review) |
| Manual | 90 | yes (user action) |
| Scrape | 10 | no (review) |

> Σημ.: Manual priority είναι υψηλή, αλλά το structured list μπορεί να θεωρηθεί “authoritative” όπου έχει συμφωνηθεί.
