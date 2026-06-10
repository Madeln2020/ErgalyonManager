# Ergalyon Data Manager (EDM)

> Σύστημα διαχείρισης δεδομένων προϊόντων & εργαλείων για την **Ergalyon**.

Το **Ergalyon Data Manager (EDM)** είναι μια πλατφόρμα που αυτοματοποιεί την
εισαγωγή, τον καθαρισμό, την κατηγοριοποίηση και τον εμπλουτισμό δεδομένων
προϊόντων που προέρχονται από διαφορετικές πηγές προμηθευτών (τιμολόγια PDF,
XML, κατάλογοι, λίστες Excel, εικόνες με OCR κ.ά.). Στόχος είναι η δημιουργία
μιας ενιαίας, αξιόπιστης και αναζητήσιμης βάσης δεδομένων εργαλείων με
μοναδικό **Κωδικό Εργαλύων (ERG-XXXXXXXX)** για κάθε προϊόν.

---

## 📋 Επισκόπηση

Το EDM καλύπτει ολόκληρη τη ροή δεδομένων:

- **Εισαγωγή (Ingestion):** Πολυμορφική υποστήριξη αρχείων (PDF, XML, Excel, εικόνες).
- **Parsing & Normalization:** Εξαγωγή και κανονικοποίηση περιγραφών προϊόντων.
- **Κατηγοριοποίηση:** Αυτόματη ταξινόμηση 3 επιπέδων (Κ1 / Κ2 / Κ3) με ML confidence score.
- **Review Queue:** Ανθρώπινη επιβεβαίωση για αμφίβολες εγγραφές.
- **Supplier Rule Engine:** Κανόνες ανά προμηθευτή (π.χ. Poimenidis).
- **Εμπλουτισμός & Εξαγωγή:** Τιμές, barcodes, εικόνες, εξαγωγή σε CSV/JSON/API.

---

## 📂 Δομή Τεκμηρίωσης

```
.
├── README.md                          # Αυτό το αρχείο
├── split_specifications.py            # Script διαχωρισμού του master spec
├── .gitignore
└── docs/
    ├── EDM_Developer_Alignment_Brief.docx   # Brief ευθυγράμμισης για developers
    ├── specifications/
    │   └── EDM_Master_Specification.md       # Πλήρης τεχνική προδιαγραφή (master)
    ├── reference/                            # Πηγαία έγγραφα αναφοράς
    │   ├── Ergalyon_Executive_Summary.pdf
    │   ├── Ergalyon_Developer_Documentation.pdf
    │   ├── ΤΔΣ7310.pdf
    │   ├── ΤΙΣ12.pdf
    │   ├── ΚΑΤΗΓΟΡΙΟΠΟΙΗΣΗ.xlsx
    │   └── από CSV σε Excel 2026-4-27.xlsx
    └── assets/                               # Εικόνες / screenshots
        ├── dell_specs_1.png
        ├── dell_specs_2.png
        ├── dell_specs_3.png
        └── dell_specs_4.png
```

➡️ **Master Specification:** [`docs/specifications/EDM_Master_Specification.md`](docs/specifications/EDM_Master_Specification.md)

---

## 🚀 Quick Start

```bash
# 1. Clone το repository
git clone https://github.com/Madeln2020/ErgalyonManager.git
cd ErgalyonManager

# 2. (Προαιρετικό) Διάσπαση του master specification σε επιμέρους αρχεία ενοτήτων
python3 split_specifications.py

# 3. Δείτε τα παραγόμενα αρχεία προδιαγραφών
ls docs/specifications/
```

Το script `split_specifications.py` διαβάζει το master specification και το
χωρίζει σε αριθμημένα αρχεία ανά ενότητα (`01_Functional_Specification.md`,
`02_Domain_Model.md`, …). Δείτε τα σχόλια στην κορυφή του script για πλήρεις
οδηγίες χρήσης (`python3 split_specifications.py --help`).

---

## 📑 Ενότητες Προδιαγραφής (Master Spec)

Οι παρακάτω ενότητες ορίζονται στο master specification. Όσες ενότητες έχουν
ολοκληρωθεί διαχωρίζονται σε ξεχωριστά αρχεία μέσω του `split_specifications.py`.

| # | Ενότητα | Αρχείο μετά το split |
|---|---------|----------------------|
| 1 | [Functional Specification](docs/specifications/EDM_Master_Specification.md#1-functional-specification) | `01_Functional_Specification.md` |
| 2 | [Domain Model](docs/specifications/EDM_Master_Specification.md#2-domain-model) | `02_Domain_Model.md` |
| 3 | [Entity Definitions](docs/specifications/EDM_Master_Specification.md#3-entity-definitions) | `03_Entity_Definitions.md` |
| 4 | Event Specification | `04_Event_Specification.md` |
| 5 | Database Design | `05_Database_Design.md` |
| 6 | API Contracts | `06_API_Contracts.md` |
| 7 | Review Queue Specification | `07_Review_Queue_Specification.md` |
| 8 | Supplier Rule Engine Specification | `08_Supplier_Rule_Engine_Specification.md` |
| 9 | Parsing Strategy | `09_Parsing_Strategy.md` |
| 10 | UI/UX Specification | `10_UIUX_Specification.md` |
| 11 | Implementation Roadmap | `11_Implementation_Roadmap.md` |

> ℹ️ Το master specification είναι **living document**. Ορισμένες ενότητες (4–11)
> ενδέχεται να βρίσκονται ακόμη υπό συγγραφή· το `split_specifications.py`
> παράγει αρχεία μόνο για όσες ενότητες υπάρχουν και προειδοποιεί για τις
> υπόλοιπες.

---

## 🛠️ Tech Stack

Η αρχιτεκτονική του EDM βασίζεται σε:

| Επίπεδο | Τεχνολογίες (προτεινόμενες) |
|---------|------------------------------|
| **Backend** | Python (FastAPI), Node.js |
| **Database** | PostgreSQL (σχεσιακό μοντέλο με UUID primary keys) |
| **Parsing / OCR** | PDF parsers, XML parsers, OCR engine για εικόνες, Excel readers |
| **ML / Κατηγοριοποίηση** | Μοντέλα ταξινόμησης 3 επιπέδων με confidence scoring |
| **Frontend** | Web UI (Upload Flow, Product Management, Review Queue, Search) |
| **Deployment** | Plesk + Git integration (domain: `pylon.ergalyon.com`) |

> Οι τελικές επιλογές τεχνολογιών τεκμηριώνονται αναλυτικά στις ενότητες
> *Database Design*, *API Contracts* και *UI/UX Specification* του master spec.

---

## ⚙️ Development Setup

> _Placeholder — οι αναλυτικές οδηγίες ρύθμισης περιβάλλοντος ανάπτυξης θα
> προστεθούν καθώς ολοκληρώνεται η αρχιτεκτονική._

```bash
# Python environment (placeholder)
python3 -m venv .venv
source .venv/bin/activate
# pip install -r requirements.txt

# Node.js dependencies (placeholder)
# npm install

# Environment variables (placeholder)
# cp .env.example .env

# Database (placeholder)
# Εκτέλεση migrations / seed data
```

---

## 🤝 Συνεισφορά

1. Διαβάστε το [`docs/EDM_Developer_Alignment_Brief.docx`](docs/EDM_Developer_Alignment_Brief.docx).
2. Μελετήστε το [Master Specification](docs/specifications/EDM_Master_Specification.md).
3. Δημιουργήστε feature branch και ανοίξτε Pull Request προς `main`.

---

## 📄 Άδεια Χρήσης

Proprietary — © Ergalyon. Με επιφύλαξη παντός δικαιώματος.
