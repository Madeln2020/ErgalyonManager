# 06 — Normalization & Matching

## 6.1 Normalization
Normalization = μετατροπή raw πεδίων σε canonical μορφή.

### 6.1.1 SKU normalization
- trimming, uppercase
- αφαίρεση “noise” (spaces, non-breaking spaces)
- αφαίρεση supplier prefixes (κανόνας ανά supplier)
- normalize separators (`-`, `/`, `.`)

### 6.1.2 Description normalization
- collapse whitespace
- normalize Greek/Latin lookalikes (προαιρετικό)

### 6.1.3 Units & decimals
- `1,50` → `1.50`
- detect unit from description (optional)

## 6.2 Matching invariants (LOCK)
- Primary identity signals:
  - `supplier_sku_normalized`
  - manufacturer code (όταν παρέχεται)
- **Δεν** χρησιμοποιείται Pylon internal code ως core identity.

## 6.3 Matching algorithm (recommended)
### Stage 1 — Exact link
Lookup `ProductSupplierLink` by `(supplier_id, supplier_sku_normalized)`.

- If found → match (auto_exact)

### Stage 2 — Candidate generation
If not found:

- search for close SKUs within same supplier
- optionally use embeddings on description to retrieve top candidates
- optionally use past manual overrides as signals

### Stage 3 — Decision policy
- if score >= `AUTO_MATCH_THRESHOLD`: propose match but still open review unless supplier is “trusted mode”
- if score between thresholds: suggest candidates → review required
- if score low: “create provisional product” path

## 6.4 Handling duplicates
- Two different supplier SKUs might refer to same product (rare).
- Policy: require manual merge action.

## 6.5 Provisional product flow
When no match:
1. Create Product with status `provisional`.
2. Create ProductSupplierLink.
3. Add ReviewTask “enrichment_confirm”.

## 6.6 Audit of decisions
Every match decision records:
- candidates
- scores
- chosen target
- user
- timestamp

## 6.7 Human override rules
- Manual override is final.
- Future automation must respect override until rule updated.
