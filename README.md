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
|| **Backend** | Python (FastAPI), Beautiful Soup, Requests, Celery, SQLAlchemy, PostgreSQL, Prometheus client ||
|| **Database** | PostgreSQL (σχεσιακό μοντέλο με UUID primary keys) + Redis (caching layer) ||
|| **Parsing / OCR** | PDF parsers, XML parsers, OCR engine για εικόνες, Excel readers, Vision API (Google Cloud) ||
|| **Web Scraping** | Requests + BeautifulSoup4 ||
|| **AI Services** | RAG (PostgreSQL full‑text), Celery async worker, OCR pipeline (planned LLM integration) ||
|| **Frontend** | Web UI (Upload Flow, Product Management, Review Queue, Recommended Scraping) with loading states and skeleton screens (planned real-time updates) ||
|| **Deployment** | Plesk + Git integration (domain: `pylon.ergalyon.com`), Docker Compose for local development ||

> Οι τελικές επιλογές τεχνολογιών τεκμηριώνονται αναλυτικά στις ενότητες
> *Database Design*, *API Contracts* και *UI/UX Specification* του master spec.

---

## ⚙️ Development Setup

### Local development (Python)
```bash
# 1. Clone το repository
git clone https://github.com/Madeln2020/ErgalyonManager.git
cd ErgalyonManager

# 2. Local PostgreSQL + Redis
# (Make sure PostgreSQL is running and accessible)
# (Make sure Redis is running and accessible)

# 3. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4. Install Django backend dependencies
pip install -r backend/requirements.txt

# 5. Install Node.js frontend dependencies
cd frontend
npm install
cd ..

# 6. Database migrations
cd backend
alembic upgrade head
python -m app.seed
# (Note: migration 004_perf_indexes adds performance indexes)
cd ..

# 7. Start the backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8887
# (Metrics available at http://localhost:8887/metrics)

# 8. Start the frontend
cd frontend
npm run dev
```

### Production (Docker Compose)
```bash
# 1. Clone το repository
git clone https://github.com/Madeln2020/ErgalyonManager.git
cd ErgalyonManager

# 2. Ensure Docker & Docker Compose are installed

# 3. Database & Redis already defined in docker-compose.yml
# (and automatically created on first start)

# 4. Start all services
docker-compose up -d
# (Backend metrics at http://localhost:8887/metrics, logs are structured JSON)

# 5. Access the frontend
open http://localhost:3000

# 6. Access the backend API docs
open http://localhost:8887/docs

# 7. Access the Celery worker logs (keep separate terminal)
docker-compose logs -f celery_worker
```

## 📦 API Endpoints

### Scrape (Web Scraping)
- **POST** `/api/v1/scrape/`  
  Scrapes products from a URL using a CSS selector.  
  Request body:  
  ```json
  {
    "url": "https://example.com/products",
    "selector": ".product-item"
  }
  ```  
  Response:  
  ```json
  [
    {
      "title": "Product Name",
      "sku": "SKU123",
      "price": 99.99,
      "image_url": "https://example.com/image.jpg",
      "source_url": "https://example.com/products"
    }
  ]
  ```

### RAG (Retrieval-Augmented Generation)
- **POST** `/api/v1/rag/search`  
  Performs a full‑text search in the products table context (e.g., description field).  
  Request body:  
  ```json
  {
    "query": "drill",
    "limit": 5
  }
  ```  
  Response:  
  ```json
  {
    "results": [...]
  }
  ```

- **POST** `/api/v1/catalogs/{product_id}/rag-enrich`  
  Enriches a catalog product with additional context. Placeholder implementation – will require LLM integration in a later stage.

### Processing Pipeline
- The OCR image parser (`_process_image`) uses a **confidence threshold of 0.85**.  
  - If confidence >= 0.85 → results are returned directly (lazy status: `queued: false`).  
  - If confidence < 0.85 → the raw OCR text is enqueued as a Celery task (`enrich_product_task`) and the response includes `queued: true`.  

### Celery
- **Worker command** (local):  
  ```bash
  celery -A backend.celery_worker.celery_app worker --loglevel=info
  ```  
- **Worker command** (Docker):  
  ```bash
  docker-compose up -d celery_worker
  ```  
- Main task: `enrich_product_task(product_id, raw_text)` → stores raw context into `rag_context` column of the Product table.

### Supplier Agreements
- POST `/api/v1/supplier-agreements/upload` – upload agreement file (PDF/DOCX/TXT)
- GET `/api/v1/supplier-agreements` – list agreements (filter by supplier_id)
- GET `/api/v1/supplier-agreements/{id}` – get single agreement
- POST `/api/v1/supplier-agreements/search` – full‑text search over agreement titles and content
- DELETE `/api/v1/supplier-agreements/{id}` – delete agreement and file

### Metrics
- GET `/metrics` – Prometheus metrics endpoint (exposes request counts, latency, DB query stats, background job stats)
- GET `/health` – Health check endpoint returning DB and Redis status.

---

## 🤝 Συνεισφορά

1. Διαβάστε το [`docs/EDM_Developer_Alignment_Brief.docx`](docs/EDM_Developer_Alignment_Brief.docx).
2. Μελετήστε το [Master Specification](docs/specifications/EDM_Master_Specification.md).
3. Δημιουργήστε feature branch και ανοίξτε Pull Request προς `main`.

---

## 📄 Άδεια Χρήσης

Proprietary — © Ergalyon. Με επιφύλαξη παντός δικαιώματος.
