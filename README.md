# Ergalyon Invoice Manager (EDM v2)

## 1) TL;DR
Το **EDM v2** είναι ένα σύστημα διαχείρισης παραστατικών/δεδομένων προμηθευτών που:

- δέχεται **αρχεία εισόδου** (π.χ. τιμολόγια/προσφορές σε PDF, XML, Excel, φωτογραφίες),
- κάνει **εξαγωγή γραμμών** (items) και βασικών πεδίων,
- εφαρμόζει **deterministic κανόνες ανά προμηθευτή** (normalization),
- κάνει **matching** σε υπάρχοντα προϊόντα μέσω supplier/manufacturer κωδικών (όχι μέσω Pylon codes),
- επιτρέπει **human review** (ουρά ελέγχου/διόρθωσης),
- κάνει **enrichment** προϊόντων με αυστηρή ιεράρχηση πηγών (XML/λίστες/κατάλογοι → manual → scraping τελευταίο),
- παράγει **exports** για downstream χρήση (μορφές που θα συμφωνηθούν) με έλεγχο εγκυρότητας.

> Σημείωση: Το EDM v2 **ΔΕΝ** κάνει compliance/dispute (π.χ. “σύγκριση συμφωνητικού με τιμολόγιο”) εκτός αν προστεθεί ρητά σε μελλοντική έκδοση.

## 2) Περιεχόμενα documentation (πρόταση)
Το documentation βρίσκεται σε αρχεία Markdown. Στο GitHub πρότεινε να τα βάλεις στο `/docs/`.

- `docs/00_product_brief.md`
- `docs/01_scope_and_non_goals.md`
- `docs/02_system_architecture.md`
- `docs/03_data_model.md`
- `docs/04_end_to_end_workflow.md`
- `docs/05_parsing_and_extraction.md`
- `docs/06_normalization_and_matching.md`
- `docs/07_enrichment_pipeline.md`
- `docs/08_review_queue_and_ui.md`
- `docs/09_exports.md`
- `docs/10_supplier_rules_poimenidis.md`
- `docs/11_ai_strategy_hermes_routing.md`
- `docs/12_security_privacy_audit.md`
- `docs/13_testing_acceptance_metrics.md`
- `docs/14_ops_runbooks_release.md`
- `docs/15_roadmap_backlog.md`
- `docs/16_glossary.md`

## 3) Πώς να ξεκινήσει το dev
1. **Διαβάστε**: `docs/00_product_brief.md` + `docs/01_scope_and_non_goals.md`.
2. **Κλειδώστε**: κανόνες “Truth & Precedence” στο `docs/07_enrichment_pipeline.md`.
3. **Υλοποιήστε το MVP core**: parsing → normalization → matching → review → export για **Poimenidis**.
4. Προσθέστε δεύτερο supplier μόνο αφού περάσουν τα acceptance tests (βλ. `docs/13_testing_acceptance_metrics.md`).

## 4) Βασικές αρχές υλοποίησης (κανόνες)
- **Deterministic-first**: Ό,τι γίνεται με κανόνες/regex/πίνακες αντιστοίχισης, γίνεται deterministic.
- **AI ως υποβοήθηση**: AI βοηθά σε extraction/normalization suggestions και όχι ως “source of truth”.
- **Provenance παντού**: κάθε πεδίο έχει πηγή (XML/PDF/manual/scrape), timestamp, user.
- **Human-in-the-loop**: τίποτα κρίσιμο δεν “κλειδώνει” χωρίς review όταν υπάρχει ambiguity.

## 5) Πρώτος Supplier Pilot
- **Poimenidis**
- Κανόνας κωδικού: το manufacturer code = supplier code χωρίς prefix `03-`.

Δες: `docs/10_supplier_rules_poimenidis.md`
