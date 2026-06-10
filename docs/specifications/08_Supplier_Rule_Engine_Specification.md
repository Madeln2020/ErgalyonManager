## 8. Supplier Rule Engine Specification

Το Supplier Rule Engine επιτρέπει ανά-προμηθευτή προσαρμογή της επεξεργασίας **πριν** τη δημιουργία/ενημέρωση προϊόντος. Οι κανόνες είναι **declarative** (JSON), versioned, και εφαρμόζονται ντετερμινιστικά με σαφή σειρά προτεραιότητας.

### 8.1 Rule Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  SUPPLIER RULE ENGINE FLOW                   │
└─────────────────────────────────────────────────────────────┘

  InvoiceItem (raw)                supplier.rules_json
        │                                  │
        ▼                                  ▼
  ┌───────────────────────────────────────────────┐
  │            RULE ENGINE PIPELINE                │
  │                                                │
  │  1. Load rules (sorted by priority ASC)        │
  │  2. field_mapping     → map columns/fields     │
  │  3. code_normalization→ clean/transform codes  │
  │  4. validation        → check format/required  │
  │  5. enrichment_hint    → where to find specs   │
  │                                                │
  └───────────────────┬───────────────────────────┘
                      ▼
            Normalized InvoiceItem
       (normalized_supplier_code, mapped fields)
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
     validation pass      validation fail
            │                   │
       Product C/U         ReviewQueueItem
```

**Εφαρμογή:** Το engine φορτώνει τα rules από το `suppliers.rules_json` (denormalized) — αλλά η authoritative/versioned πηγή είναι ο πίνακας `supplier_rules`. Τα rules εφαρμόζονται με αύξουσα σειρά `priority` (χαμηλότερο = πρώτο).

### 8.2 Rule Types

#### 8.2.1 code_normalization
Καθαρισμός/μετασχηματισμός κωδικών.

| type | params | περιγραφή |
|------|--------|-----------|
| `strip_prefix` | `prefix` | Αφαίρεση prefix (π.χ. `03-`) |
| `strip_suffix` | `suffix` | Αφαίρεση suffix |
| `regex_replace` | `pattern`, `replacement` | Γενικός regex μετασχηματισμός |
| `pad_left` | `length`, `char` | Zero-padding |
| `uppercase` / `trim` | — | Κανονικοποίηση μορφής |

#### 8.2.2 field_mapping
Αντιστοίχιση custom στηλών/πεδίων του προμηθευτή στα EDM fields.
```json
{ "type": "field_mapping",
  "map": { "ΚΩΔΙΚΟΣ": "supplier_code", "ΠΕΡΙΓΡΑΦΗ": "raw_description", "ΤΙΜΗ": "unit_price" } }
```

#### 8.2.3 validation
Έλεγχοι μορφής/υποχρεωτικότητας. Αποτυχία → ReviewQueueItem.
```json
{ "type": "validation",
  "field": "normalized_supplier_code",
  "rules": [{ "required": true }, { "regex": "^[0-9]{4,8}$" }] }
```

#### 8.2.4 enrichment_hint
Υποδείξεις για το πού θα βρεθούν specs/manufacturer codes.
```json
{ "type": "enrichment_hint",
  "manufacturer_code_source": "scraping",
  "scrape_url_template": "https://poimenidis.gr/product/{supplier_code}" }
```

### 8.3 Poimenidis Rules (πρώτη υλοποίηση)

Ο Poimenidis είναι το **πρώτο test case**: έχει XML τιμολόγια, φωτογραφίες, και website για scraping. Ο βασικός κανόνας είναι ντετερμινιστικός — αφαίρεση του `03-` prefix.

```json
{
  "supplier": "Poimenidis",
  "parsing_profile": "xml",
  "rules": [
    {
      "type": "code_normalization",
      "priority": 10,
      "operations": [
        { "op": "strip_prefix", "prefix": "03-" },
        { "op": "trim" }
      ],
      "description": "Poimenidis κωδικοί: 03-12345 → 12345 (deterministic, 100% confidence)"
    },
    {
      "type": "validation",
      "priority": 20,
      "field": "normalized_supplier_code",
      "rules": [{ "required": true }, { "regex": "^[0-9]+$" }]
    },
    {
      "type": "enrichment_hint",
      "priority": 30,
      "manufacturer_code_source": "scraping",
      "scrape_url_template": "https://www.poimenidis.gr/search?q={supplier_code}"
    }
  ]
}
```

**Παράδειγμα εφαρμογής:**
```
Input raw_supplier_code: "03-12345"
  → strip_prefix "03-"  → "12345"
  → trim                → "12345"
Output normalized_supplier_code: "12345"   (confidence: 100%, no review needed)
```

### 8.4 Rule Configuration

**Αποθήκευση:**
- Authoritative: πίνακας `supplier_rules` (versioned, audit μέσω `audit_log`)
- Runtime cache: `suppliers.rules_json` (denormalized, ανανεώνεται σε κάθε `rule.created`/`rule.updated`)

**Precedence & Composition:**
```
1. Εκτέλεση κατά αύξον priority (10, 20, 30, ...)
2. Μέσα στο ίδιο rule, τα operations εκτελούνται με τη σειρά του array
3. field_mapping ΠΑΝΤΑ πρώτα (lowest priority number)
4. validation ΠΑΝΤΑ μετά τα normalization
5. Σύγκρουση δύο rules → event rule.conflict → ReviewQueueItem
```

**Lifecycle:**
- Νέος κανόνας: `POST/PUT /suppliers/{id}` με `rules_json` → event `rule.created`/`rule.updated`
- Δοκιμή κανόνα (dry-run): preview πεδίο στο UI πριν το save (βλ. §10.2)
- Versioning: κάθε αλλαγή κρατά παλιά έκδοση στο `supplier_rules` (soft-update via `is_active`)

> **Αρχή σχεδίασης:** Όλοι οι deterministic κανόνες (όπως ο Poimenidis `03-`) τρέχουν με 100% confidence και ΔΕΝ δημιουργούν review items. Μόνο τα ambiguous/probabilistic αποτελέσματα πάνε στη Review Queue.


---
