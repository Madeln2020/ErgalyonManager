# 10 — Supplier Rules: Poimenidis (Pilot)

## 10.1 Scope
Αυτό το αρχείο είναι ο “κανόνας” για τον πρώτο supplier pilot.

## 10.2 Known inputs
- invoices με σωστή δομή
- XML (υπάρχει)
- φωτογραφίες
- website για search

## 10.3 Critical deterministic rule (LOCK)
**Manufacturer code = supplier code χωρίς το prefix `03-`.**

### 10.3.1 Normalization function
- Input: `supplier_sku_raw`
- Output: `supplier_sku_normalized`

Rule:
- Αν ξεκινάει με `03-` → αφαιρείται το `03-`
- Αλλιώς → unchanged

Παραδείγματα:
- `03-12345` → `12345`
- `03-AB-778` → `AB-778`
- `12345` → `12345`

### 10.3.2 Additional cleanup (recommended)
- trim
- collapse spaces
- uppercase

## 10.4 Matching policy for Poimenidis
- Stage 1 exact match on normalized SKU
- If no match → review required

## 10.5 XML fields precedence
- Ό,τι έρχεται από XML (structured) υπερισχύει των PDF extractions.

## 10.6 Website scraping usage
- μόνο όταν:
  - δεν υπάρχει XML/list/catalog data για το product
  - και ο χρήστης το επιλέγει ή υπάρχει task “need_enrichment”

## 10.7 Test dataset requirements
Για να θεωρήσουμε ότι ο κανόνας δουλεύει:
- τουλάχιστον N invoices
- coverage σε SKUs με και χωρίς prefix
- mixture σε line formats

## 10.8 Acceptance criteria
- >= 95% σωστό normalization
- >= 90% exact match rate σε γνωστά προϊόντα (μετά από αρχικό setup)
- extraction accuracy για qty/unit_price >= 98% σε XML cases
