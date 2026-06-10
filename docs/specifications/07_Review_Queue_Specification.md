## 7. Review Queue Specification

Η Review Queue είναι το **human-in-the-loop** κέντρο του EDM. Όταν το αυτόματο processing δεν είναι αρκετά σίγουρο, το item μπαίνει σε ουρά για ανθρώπινη απόφαση. Οι αποφάσεις του χρήστη **υπερισχύουν τα πάντα** (manual = highest precedence) και τροφοδοτούν το learning loop.

### 7.1 Review Triggers

Ένα `ReviewQueueItem` δημιουργείται αυτόματα όταν συμβεί μία από τις παρακάτω συνθήκες:

| Trigger | review_type | Priority | Συνθήκη |
|---------|-------------|----------|---------|
| Χαμηλό parsing confidence | `low_confidence` | HIGH | `parsing_confidence < 90%` ή `match_confidence < 85%` |
| Χαμηλό category confidence | `low_confidence` | HIGH | `category_confidence < 85%` (RULE C2) |
| Πιθανό duplicate | `duplicate` | CRITICAL | Ίδιο `supplier_code` ή πολύ όμοια περιγραφή (trigram similarity > 0.9) |
| Λείπει manufacturer code | `missing_manufacturer_code` | HIGH | Product έχει supplier_code αλλά όχι manufacturer_code μετά το enrichment |
| Ανωμαλία τιμής | `price_anomaly` | MEDIUM | Νέα τιμή αποκλίνει > 50% από την προηγούμενη (RULE R1) |
| Νέος προμηθευτής | `new_supplier` | MEDIUM | Τα πρώτα 50 προϊόντα νέου supplier (RULE R1) |

> **Σημείωση:** Όλοι οι deterministic κανόνες (π.χ. Poimenidis `03-` prefix removal) **δεν** δημιουργούν review items — εφαρμόζονται αυτόματα με 100% confidence.

### 7.2 Review Workflow

```
┌──────────────┐
│  Auto-detect │  trigger condition (§7.1)
│   trigger    │
└──────┬───────┘
       │ create ReviewQueueItem (status=open)
       ▼
┌──────────────┐    χρήστης ανοίγει το item
│   OPEN       │───────────────────────────────┐
└──────────────┘                               ▼
                                       ┌────────────────┐
                                       │  IN_PROGRESS   │
                                       │  (assigned)    │
                                       └───────┬────────┘
                          ┌────────────────────┼────────────────────┐
                          ▼                     ▼                    ▼
                    ┌──────────┐         ┌──────────┐         ┌──────────┐
                    │ APPROVE  │         │   EDIT   │         │  REJECT  │
                    └────┬─────┘         └────┬─────┘         └────┬─────┘
                         │                    │                    │
              train ML (positive)   create manual source   back to parsing
                         │            (overrides all)             │
                         ▼                    ▼                    ▼
                    ┌─────────────────────────────────────────────────┐
                    │              RESOLVED / DISMISSED                │
                    └─────────────────────────────────────────────────┘
```

**Resolution actions (RULE R3):**
- **Approve:** Επιβεβαιώνει τις προτεινόμενες τιμές → θετικό feedback στο ML model.
- **Edit:** Ο χρήστης διορθώνει → δημιουργεί `source=manual` εγγραφή (υπερισχύει XML/Catalog/Scraping).
- **Reject:** Επιστρέφει το item για re-parsing ή το επισημαίνει ως άκυρο.
- **Dismiss:** Το item κρίθηκε μη σχετικό (false positive).

### 7.3 Review Types (αναλυτικά)

#### 7.3.1 missing_manufacturer_code — Το κρίσιμο prompt
Όταν ένα προϊόν έχει `supplier_code` αλλά κανένα `manufacturer_code` μετά το enrichment, και ο supplier code μοιάζει με κωδικό κατασκευαστή (π.χ. αλφαριθμητικό μοτίβο τύπου brand), το σύστημα ρωτά:

> **«Θα χρησιμοποιηθεί ο κωδικός προμηθευτή ως κωδικός κατασκευαστή;»**

```json
{
  "review_type": "missing_manufacturer_code",
  "priority": "HIGH",
  "prompt_text": "Θα χρησιμοποιηθεί ο κωδικός προμηθευτή ως κωδικός κατασκευαστή;",
  "payload": {
    "supplier_code": "2607336",
    "description": "ΛΑΜΑ ΣΕΓΑΣ BOSCH",
    "options": ["Ναι, χρήση ως manufacturer code",
                "Όχι, το προϊόν δεν έχει manufacturer code",
                "Εισαγωγή χειροκίνητα"]
  }
}
```
Resolution payload: `{ "use_supplier_code_as_manufacturer": true }` → set `manufacturer_code = supplier_code`, `manufacturer_flag = true`.

#### 7.3.2 duplicate
Εμφανίζει side-by-side το υπάρχον vs το νέο product· ο χρήστης επιλέγει merge ή keep-separate.

#### 7.3.3 low_confidence (category)
Εμφανίζει top-3 ML προτάσεις K1/K2/K3 με τα confidence scores· ο χρήστης επιλέγει ή διορθώνει.

#### 7.3.4 price_anomaly
Εμφανίζει το ιστορικό τιμών (PriceHistory) με γράφημα· ο χρήστης επιβεβαιώνει ή απορρίπτει.

### 7.4 Priority Rules

```
PRIORITY ORDER (descending):
  CRITICAL  → duplicate detection, validation errors  (block export)
  HIGH      → missing manufacturer code, low ML/parse confidence
  MEDIUM    → price anomalies, new supplier
  LOW       → enrichment opportunities

SORTING στο queue:
  ORDER BY priority_rank ASC, created_at ASC   (oldest critical first)

SLA / Escalation:
  - CRITICAL ανοιχτό > 24h  → notification
  - HIGH ανοιχτό > 72h      → priority bump / notification
  - Auto-escalation event: review.escalated (§4.1.4)

BLOCKING:
  - Invoice ΔΕΝ μπορεί να φτάσει σε status=reviewed
    όσο υπάρχουν open CRITICAL/HIGH review items (§4.2 guard)
```


---
