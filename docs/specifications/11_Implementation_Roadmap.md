## 11. Implementation Roadmap

Αυτή η ενότητα περιγράφει το πλάνο υλοποίησης (implementation roadmap) του Ergalyon Data Manager (EDM), χωρισμένο σε διακριτές φάσεις (phases). Κάθε φάση έχει σαφή στόχο (goal), παραδοτέα (deliverables), milestones και κριτήρια αποδοχής (acceptance criteria). Η προσέγγιση είναι incremental: κάθε φάση παραδίδει λειτουργικό προϊόν που μπορεί να χρησιμοποιηθεί παραγωγικά πριν ξεκινήσει η επόμενη.

**Αρχές roadmap:**
- **Vertical slices:** Κάθε φάση παραδίδει ολοκληρωμένη end-to-end ροή (upload → parse → review → product → export), όχι μεμονωμένα τεχνικά layers.
- **Πραγματικά δεδομένα νωρίς:** Ο πρώτος προμηθευτής (Ποιμενίδης) χρησιμοποιείται ως test case από τη Φάση 1, ώστε να επικυρώνονται οι παραδοχές με αληθινά τιμολόγια.
- **Risk-first:** Τα πιο αβέβαια τεχνικά κομμάτια (OCR, vision parsing, RAG) έρχονται αφού σταθεροποιηθεί η deterministic ροή (XML/myDATA).

---

### 11.1 Φάση 0 — Foundation & Setup (Προετοιμασία)

**Στόχος:** Στήσιμο του τεχνικού υπόβαθρου ώστε οι επόμενες φάσεις να αναπτύσσονται γρήγορα και αξιόπιστα.

**Διάρκεια (εκτίμηση):** 1–2 εβδομάδες.

**Deliverables:**
- Repository structure & monorepo layout (backend `FastAPI`, frontend `Next.js`, shared schemas).
- Infrastructure provisioning: Hetzner server (UI + PostgreSQL + Redis/Queue), Dell laptop node (AI/OCR/scraping workers) — σύμφωνα με §2 Architecture.
- PostgreSQL schema migrations (Alembic) για τους core πίνακες της §5: `products`, `suppliers`, `invoices`, `invoice_items`, `product_source_data`, `review_queue`, `supplier_agreements`, `categories`, `product_specifications`.
- CI/CD pipeline (lint, tests, build) + environment configuration (`.env` management, secrets).
- Celery + Redis worker setup με ένα health-check task.
- Base authentication/authorization skeleton.

**Milestones:**
- M0.1: Repo + local dev environment τρέχει με `docker-compose`.
- M0.2: Migrations εφαρμόζονται καθαρά σε άδεια βάση.
- M0.3: Backend ↔ Worker ↔ DB ↔ Redis επικοινωνούν (smoke test).

**Acceptance criteria:**
- Ένας developer μπορεί να κάνει clone + `make dev` και να έχει λειτουργικό περιβάλλον σε < 30 λεπτά.
- Όλα τα tables της §5 υπάρχουν με τα indexes/constraints των §5.3–5.4.

---

### 11.2 Φάση 1 — Poimenidis MVP (Deterministic Pipeline)

**Στόχος:** Πλήρης end-to-end ροή για έναν προμηθευτή (Ποιμενίδης) με deterministic δεδομένα (XML/myDATA), χειροκίνητο review και βασική διαχείριση προϊόντων. Αυτή η φάση αποδεικνύει το core value proposition του EDM.

**Διάρκεια (εκτίμηση):** 3–4 εβδομάδες.

**Scope (in):**
- **XML/myDATA parser** (§9.1): ανάγνωση δομημένων τιμολογίων Ποιμενίδη με υψηλό confidence.
- **Supplier Rule Engine — βασικό** (§8): υλοποίηση του deterministic κανόνα Ποιμενίδη (αφαίρεση προθέματος `03-` από τον κωδικό προμηθευτή → κωδικός κατασκευαστή, RULE P1).
- **Triple-code model** (§3): Ergalyon code (unique, εσωτερικός), Supplier code (υποχρεωτικός), Manufacturer code (προαιρετικός).
- **Mandatory user prompt** (§7.3.1, §10.4): «Θα χρησιμοποιηθεί ο κωδικός προμηθευτή ως κωδικός κατασκευαστή;» όταν ο κανόνας δεν παράγει κωδικό κατασκευαστή.
- **Review Queue — manual** (§7): ουρά ελέγχου με βασικά flags (διπλότυπα, ασυνήθιστες τιμές, ελλιπή πεδία) και actions Approve/Edit/Reject.
- **Product management** (§10.3): λίστα/προβολή/επεξεργασία προϊόντων, source precedence Manual > XML > Catalog > Scraping (§3, §9.7).
- **Upload flow** (§10.2) + **Export** (CSV/Excel) για χρήση σε εξωτερικά συστήματα.
- **Core REST API** (§6) για τα παραπάνω.

**Scope (out):** OCR, vision/catalog parsing, scraping, RAG agreements, multi-supplier rules, category ML.

**Deliverables:**
- Λειτουργικό web app όπου ο χρήστης ανεβάζει τιμολόγιο Ποιμενίδη (XML), τα items περνούν parse + normalization + rule engine, εμφανίζονται στην ουρά ελέγχου, και μετά την έγκριση ενημερώνουν τα προϊόντα.
- Export ενημερωμένου καταλόγου προϊόντων.

**Milestones:**
- M1.1: XML parser εξάγει σωστά items από δείγμα τιμολογίων Ποιμενίδη (≥ 95% πεδίων).
- M1.2: Rule engine παράγει σωστό κωδικό κατασκευαστή (RULE P1) + ενεργοποιεί το mandatory prompt στις σωστές περιπτώσεις.
- M1.3: Review queue + approve workflow ενημερώνει προϊόντα.
- M1.4: Export παράγει αρχείο έτοιμο για εξωτερική χρήση.

**Acceptance criteria:**
- Πραγματικό τιμολόγιο Ποιμενίδη επεξεργάζεται end-to-end χωρίς χειροκίνητη παρέμβαση εκτός της ουράς ελέγχου.
- Δεν δημιουργούνται διπλότυπα Ergalyon codes· τα διπλότυπα ανιχνεύονται και μπαίνουν στην ουρά (§7).
- Η αρχή source precedence τηρείται (manual edits δεν επικαλύπτονται από επόμενο XML import).

---

### 11.3 Φάση 2 — Multi-Supplier & Parser Expansion

**Στόχος:** Επέκταση πέρα από τον Ποιμενίδη: γενικευμένο rule engine για πολλαπλούς προμηθευτές και υποστήριξη περισσότερων μορφών εισόδου (PDF, Excel).

**Διάρκεια (εκτίμηση):** 4–6 εβδομάδες.

**Scope (in):**
- **Generalized Supplier Rule Engine** (§8): per-supplier configuration, σειρά εφαρμογής κανόνων, fallback σε mandatory prompt όταν δεν υπάρχει κανόνας.
- **PDF structured parser** (§9.2): εξαγωγή από PDF τιμολόγια με σταθερό layout.
- **Excel parser** (§9.5): import από spreadsheets προμηθευτών με column mapping.
- **Supplier management UI:** προσθήκη/διαχείριση προμηθευτών και των κανόνων τους.
- **Επέκταση Review Queue** (§7): supplier-specific flags, bulk approve.
- **Confidence scoring & fallback** (§9.7): ενιαία λογική για όλους τους parsers.

**Deliverables:**
- Δυνατότητα onboarding νέου προμηθευτή μέσω UI/configuration χωρίς αλλαγή κώδικα για τις τυπικές περιπτώσεις.
- Τουλάχιστον 3 προμηθευτές σε παραγωγική χρήση.

**Milestones:**
- M2.1: Rule engine υποστηρίζει N προμηθευτές με διαφορετικούς κανόνες ταυτόχρονα.
- M2.2: PDF + Excel parsers σε παραγωγή με confidence scoring.
- M2.3: Onboarding νέου προμηθευτή τεκμηριωμένο & επαναλήψιμο.

**Acceptance criteria:**
- Νέος προμηθευτής με δομημένο PDF/Excel onboardάρεται σε < 1 ημέρα.
- Τα supplier-specific rules δεν επηρεάζουν άλλους προμηθευτές (isolation).

---

### 11.4 Φάση 3 — Advanced Parsing & Intelligence

**Στόχος:** Κάλυψη των δύσκολων, μη-δομημένων πηγών δεδομένων με AI: OCR, vision-based catalog parsing, scraping και RAG πάνω στις συμφωνίες προμηθευτών.

**Διάρκεια (εκτίμηση):** 6–8 εβδομάδες.

**Scope (in):**
- **OCR parser** (§9.3): σαρωμένα/εικονοποιημένα τιμολόγια, με human-in-the-loop μέσω review queue.
- **Catalog vision parsing** (§9.4): εξαγωγή τεχνικών χαρακτηριστικών/specifications από καταλόγους (εικόνες/PDF) στους AI workers (Dell laptop node).
- **Web scraping** (§9.6): συμπλήρωση δεδομένων προϊόντων από εξωτερικές πηγές, με τη χαμηλότερη προτεραιότητα στο source precedence (§9.7).
- **RAG over Supplier Agreements** (§3, §8): retrieval-only ερωτήσεις πάνω στις συμφωνίες προμηθευτών — **χωρίς** validation, comparison ή invoice matching (out of scope, §1).
- **Product specifications** (§3.7): δομημένη αποθήκευση & εμφάνιση τεχνικών χαρακτηριστικών.

**Deliverables:**
- AI worker pipeline στο Dell node για OCR/vision/RAG.
- Δυνατότητα ερωτήσεων (Q&A) πάνω στις συμφωνίες προμηθευτών (RAG), αυστηρά retrieval.

**Milestones:**
- M3.1: OCR pipeline επεξεργάζεται σαρωμένο τιμολόγιο με fallback στην ουρά ελέγχου.
- M3.2: Catalog vision εξάγει specifications με αποδεκτό confidence.
- M3.3: RAG επιστρέφει σχετικά αποσπάσματα από τις συμφωνίες (retrieval-only).

**Acceptance criteria:**
- Χαμηλού confidence εξαγωγές κατευθύνονται πάντα στο review queue (§7) αντί να ενημερώνουν αυτόματα προϊόντα.
- Το RAG δεν εκτελεί καμία λειτουργία σύγκρισης/επικύρωσης (τήρηση scope §1).

---

### 11.5 Φάση 4 — Optimization & Scale

**Στόχος:** Βελτιστοποίηση απόδοσης, εμπειρίας χρήστη και αξιοπιστίας για παραγωγική χρήση σε κλίμακα.

**Διάρκεια (εκτίμηση):** συνεχής / 4+ εβδομάδες.

**Scope (in):**
- **Performance:** query optimization, indexing review (§5.3), caching (Redis), batch processing throughput.
- **Category ML (optional):** αυτόματη πρόταση κατηγορίας προϊόντος (§3.6) με human confirmation.
- **UX refinement** (§10): dashboards, αναφορές, βελτιωμένα bulk actions, keyboard workflows για ταχύ review.
- **Observability:** logging, metrics, alerting, audit trail πάνω στα events (§4).
- **Hardening:** rate limiting, error handling (§6.3), backup/restore, disaster recovery.

**Deliverables:**
- Production-grade monitoring & alerting.
- Τεκμηριωμένα SLOs (π.χ. χρόνος επεξεργασίας τιμολογίου, latency review queue).

**Milestones:**
- M4.1: Dashboards & metrics σε παραγωγή.
- M4.2: Καθορισμένα & μετρούμενα SLOs.
- M4.3: Τεκμηριωμένη διαδικασία backup/restore δοκιμασμένη.

**Acceptance criteria:**
- Το σύστημα διαχειρίζεται τον αναμενόμενο όγκο τιμολογίων χωρίς υποβάθμιση απόδοσης.
- Υπάρχει πλήρες audit trail για κάθε αλλαγή προϊόντος μέσω των lifecycle events (§4).

---

### 11.6 Σύνοψη Φάσεων (Phase Summary)

| Φάση | Όνομα | Κύριος στόχος | Βασικά παραδοτέα |
|------|-------|----------------|-------------------|
| 0 | Foundation & Setup | Τεχνικό υπόβαθρο | Infra, schema, CI/CD, workers |
| 1 | Poimenidis MVP | End-to-end deterministic ροή | XML parser, basic rule engine, review queue, products, export |
| 2 | Multi-Supplier & Parsers | Επέκταση σε πολλούς προμηθευτές | Generalized rule engine, PDF/Excel parsers |
| 3 | Advanced Parsing & Intelligence | Μη-δομημένες πηγές + AI | OCR, vision catalog, scraping, RAG (retrieval-only) |
| 4 | Optimization & Scale | Απόδοση, UX, αξιοπιστία | Performance, observability, hardening |

**Κρίσιμες εξαρτήσεις (dependencies):**
- Φάση 1 εξαρτάται από Φάση 0 (schema/infra).
- Φάση 2 βασίζεται στο rule engine & review queue της Φάσης 1.
- Φάση 3 (AI workers) απαιτεί σταθερό pipeline & review queue από Φάσεις 1–2 για human-in-the-loop.
- Φάση 4 διατρέχει εγκάρσια όλες τις προηγούμενες (cross-cutting).

**Out of scope σε όλες τις φάσεις** (§1): σύγκριση συμφωνίας–τιμολογίου, matching με κωδικούς Pylon ERP, write-back σε ERP, σύνταξη email, λειτουργίες διαφορών (disputes). Οι συμφωνίες προμηθευτών χρησιμοποιούνται **αποκλειστικά** για RAG retrieval.

---
