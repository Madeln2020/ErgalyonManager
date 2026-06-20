# 01 — Scope & Non‑Goals (Lock Document)

## 1.1 MUST (υποχρεωτικά)
### Intake
- Upload: PDF, XML, Excel, εικόνες.
- Συσχέτιση κάθε upload με supplier (manual επιλογή ή assisted).
- Αποθήκευση raw αρχείων (object storage) και metadata στη DB.

### Parsing / Extraction
- Εξαγωγή:
  - header πεδίων (ημερομηνία, αριθμός παραστατικού, ΑΦΜ/προμηθευτή όπου υπάρχει)
  - γραμμών (items): κωδικός, περιγραφή, ποσότητα, τιμή μονάδας, σύνολα, ΦΠΑ όπου υπάρχει.

### Normalization & Matching
- Deterministic κανόνες ανά supplier (π.χ. prefix removal).
- Matching με βάση supplier/manufacturer κωδικούς και ισχυρά deterministic signals.
- Όταν υπάρχει ασάφεια → review queue.

### Product Enrichment
- Data precedence engine (ποια πηγή “κερδίζει”).
- Enrichment από XML/λίστες/καταλόγους/manual.
- Scraping μόνο ως last resort.

### Review Queue
- UI για αποδοχή/απόρριψη/διόρθωση.
- Traceability: ποιος άλλαξε τι, πότε, γιατί.

### Export
- Παραγωγή export αρχείου/format (θα κλειδωθεί) με validation.
- Preview πριν το τελικό export.

## 1.2 SHOULD (ιδανικά)
- RAG/semantic search στα supplier documents (συμφωνητικά, catalogs).
- Bulk actions στο review.
- Price history ανά supplier.
- Model routing (Hermes) για να ελέγχεται πότε χρησιμοποιείται local vs remote AI.

## 1.3 NICE‑TO‑HAVE (μετά το MVP)
- Supplier Rule Builder UI (non-devs φτιάχνουν κανόνες).
- Ειδοποιήσεις/alerts για anomalies.
- Advanced deduplication (fuzzy matching).
- Πλήρες audit dashboard.

## 1.4 NEVER / Out of scope (για v2 όπως έχει κλειδωθεί)
- Αυτόματο “agreement vs invoice” compliance / dispute engine.
- Matching που βασίζεται σε Pylon internal codes ως primary identity.
- Αυτόματες αλλαγές χωρίς δυνατότητα review όταν υπάρχει ambiguity.

## 1.5 Δεσμεύσεις (δεδομένα)
- Κάθε τιμή/χαρακτηριστικό έχει provenance.
- Οι manual αλλαγές δεν “πατιούνται” από scraping χωρίς explicit user action.
