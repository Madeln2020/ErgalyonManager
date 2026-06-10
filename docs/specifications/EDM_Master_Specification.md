# EDM Master Specification
## Ergalyon Data Manager - Πλήρης Τεχνική Προδιαγραφή

**Έκδοση:** 1.0  
**Ημερομηνία:** 10 Ιουνίου 2026  
**Κατάσταση:** Production-Ready Specification

---

## Πίνακας Περιεχομένων

1. [Functional Specification](#1-functional-specification)
   - [1.1 Επισκόπηση Συστήματος](#11-επισκόπηση-συστήματος)
   - [1.2 End-to-End Workflow](#12-end-to-end-workflow)
   - [1.3 Βασικές Λειτουργίες](#13-βασικές-λειτουργίες)
   - [1.4 Business Rules](#14-business-rules)

2. [Domain Model](#2-domain-model)
   - [2.1 Core Entities](#21-core-entities)
   - [2.2 Entity Relationships](#22-entity-relationships)
   - [2.3 Domain Diagram](#23-domain-diagram)

3. [Entity Definitions](#3-entity-definitions)
   - [3.1 Product](#31-product)
   - [3.2 Supplier](#32-supplier)
   - [3.3 Invoice](#33-invoice)
   - [3.4 InvoiceItem](#34-invoiceitem)
   - [3.5 SupplierAgreement](#35-supplieragreement)
   - [3.6 Category](#36-category)
   - [3.7 ProductSpecification](#37-productspecification)
   - [3.8 ReviewQueueItem](#38-reviewqueueitem)

4. [Event Specification](#4-event-specification)
   - [4.1 Lifecycle Events](#41-lifecycle-events)
   - [4.2 State Transitions](#42-state-transitions)
   - [4.3 Event Handlers](#43-event-handlers)

5. [Database Design](#5-database-design)
   - [5.1 Schema Overview](#51-schema-overview)
   - [5.2 Table Definitions](#52-table-definitions)
   - [5.3 Indexes](#53-indexes)
   - [5.4 Constraints](#54-constraints)

6. [API Contracts](#6-api-contracts)
   - [6.1 REST Endpoints](#61-rest-endpoints)
   - [6.2 Request/Response Formats](#62-requestresponse-formats)
   - [6.3 Error Handling](#63-error-handling)

7. [Review Queue Specification](#7-review-queue-specification)
   - [7.1 Review Triggers](#71-review-triggers)
   - [7.2 Review Workflow](#72-review-workflow)
   - [7.3 Review Types](#73-review-types)
   - [7.4 Priority Rules](#74-priority-rules)

8. [Supplier Rule Engine Specification](#8-supplier-rule-engine-specification)
   - [8.1 Rule Architecture](#81-rule-architecture)
   - [8.2 Rule Types](#82-rule-types)
   - [8.3 Poimenidis Rules](#83-poimenidis-rules)
   - [8.4 Rule Configuration](#84-rule-configuration)

9. [Parsing Strategy](#9-parsing-strategy)
   - [9.1 Multi-Format Support](#91-multi-format-support)
   - [9.2 PDF Parsing](#92-pdf-parsing)
   - [9.3 XML Parsing](#93-xml-parsing)
   - [9.4 Image Parsing (OCR)](#94-image-parsing-ocr)
   - [9.5 Catalog PDF Parsing](#95-catalog-pdf-parsing)
   - [9.6 Excel List Parsing](#96-excel-list-parsing)

10. [UI/UX Specification](#10-uiux-specification)
    - [10.1 Screen Overview](#101-screen-overview)
    - [10.2 Upload Flow](#102-upload-flow)
    - [10.3 Product Management](#103-product-management)
    - [10.4 Review Queue Interface](#104-review-queue-interface)
    - [10.5 Search & Filtering](#105-search--filtering)

11. [Implementation Roadmap](#11-implementation-roadmap)
    - [11.1 Phase 1: Poimenidis MVP](#111-phase-1-poimenidis-mvp)
    - [11.2 Phase 2: Multi-Supplier](#112-phase-2-multi-supplier)
    - [11.3 Phase 3: Advanced Features](#113-phase-3-advanced-features)
    - [11.4 Phase 4: Optimization & Scale](#114-phase-4-optimization--scale)

---

## 1. Functional Specification

### 1.1 Επισκόπηση Συστήματος

Το **Ergalyon Data Manager (EDM)** είναι ένα εξειδικευμένο σύστημα διαχείρισης δεδομένων για τιμολόγια και προσφορές εργαλείων. Σκοπός του είναι η αυτοματοποιημένη εξαγωγή, κανονικοποίηση, εμπλουτισμός και διαχείριση δεδομένων προϊόντων από διάφορες πηγές προμηθευτών.

**Κύριοι Στόχοι:**
- Αυτοματοποίηση εξαγωγής δεδομένων από πολλαπλές μορφές εγγράφων (PDF, XML, images, Excel)
- Κανονικοποίηση δεδομένων με supplier-specific rules
- Εμπλουτισμός προϊόντων με technical specifications
- Διαχείριση 3 κωδικών ανά προϊόν (Ergalyon, Supplier, Manufacturer)
- Human-in-the-loop review workflow
- Export δεδομένων για χρήση σε άλλα συστήματα

**Τι ΔΕΝ είναι το EDM:**
- ΔΕΝ είναι ERP system
- ΔΕΝ έχει write-back integration με Pylon
- ΔΕΝ διαχειρίζεται inventory ή orders
- ΔΕΝ είναι replacement του Pylon

### 1.2 End-to-End Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    EDM COMPLETE WORKFLOW                         │
└─────────────────────────────────────────────────────────────────┘

STEP 1: SUPPLIER AGREEMENT UPLOAD
┌──────────────────────┐
│ Supplier Agreement   │ → Upload PDF/Document
│ (Συμφωνητικό)        │ → Store in RAG Archive
└──────────────────────┘ → Indexing για μελλοντική αναφορά
                         → ΟΧΙ validation checks (μόνο search)

STEP 2: INVOICE/OFFER UPLOAD
┌──────────────────────┐
│ Invoice/Offer Files  │ → Multiple formats supported
│ (Τιμολόγια/Προσφορές)│   • PDF (structured/scanned)
└──────────────────────┘   • XML (e-invoice)
                           • Images (JPG/PNG)
                           • Catalog PDFs
                           • Excel lists

STEP 3: PARSING & EXTRACTION
┌──────────────────────┐
│ Format Detection     │ → Auto-detect format
└──────────────────────┘
         ↓
┌──────────────────────┐
│ Parser Selection     │ → Route to appropriate parser
└──────────────────────┘   • PDF Parser
         ↓                 • XML Parser
┌──────────────────────┐   • OCR Engine
│ Data Extraction      │   • Catalog Parser
└──────────────────────┘   • Excel Parser
         ↓
┌──────────────────────┐
│ Raw Data Output      │ → Extracted fields:
└──────────────────────┘   • Supplier Code
                           • Product Description
                           • Price
                           • Quantity
                           • Date
                           • (Optional) Manufacturer Code

STEP 4: NORMALIZATION
┌──────────────────────┐
│ Supplier Rule Engine │ → Apply supplier-specific rules
└──────────────────────┘   Example (Poimenidis):
         ↓                 03-12345 → 12345
┌──────────────────────┐
│ Code Normalization   │ → Clean & standardize codes
└──────────────────────┘
         ↓
┌──────────────────────┐
│ Validation           │ → Check required fields
└──────────────────────┘   → Flag anomalies

STEP 5: PRODUCT CREATION/UPDATE
┌──────────────────────┐
│ Product Lookup       │ → Search by Supplier Code
└──────────────────────┘
         ↓
    ┌────┴────┐
    │ Exists? │
    └────┬────┘
    YES  │  NO
    ↓    ↓    ↓
┌────────┐  ┌──────────┐
│ UPDATE │  │  CREATE  │
└────────┘  └──────────┘
    ↓           ↓
┌──────────────────────┐
│ Source Precedence    │ → XML > Catalog > Manual > Scraping
│ Check                │ → Don't overwrite higher-quality data
└──────────────────────┘
         ↓
┌──────────────────────┐
│ Assign Κωδικός       │ → Auto-generate Ergalyon Code
│ Εργαλύων            │   (if new product)
└──────────────────────┘

STEP 6: ENRICHMENT
┌──────────────────────┐
│ Check Existing Data  │ → What's already present?
└──────────────────────┘
         ↓
┌──────────────────────┐
│ Source Selection     │ → Priority order:
└──────────────────────┘   1. XML files (if available)
         ↓                 2. Catalog PDFs
         ↓                 3. Manual input
         ↓                 4. Web scraping (fallback)
┌──────────────────────┐
│ Specification        │ → Extract technical specs
│ Extraction           │   • Dimensions
└──────────────────────┘   • Weight
         ↓                 • Material
         ↓                 • Power
         ↓                 • Capacity
┌──────────────────────┐   • Manufacturer
│ Manufacturer Code    │ → Try to find Κωδικός Κατασκευαστή
│ Discovery            │
└──────────────────────┘
         ↓
┌──────────────────────┐
│ Flag Check           │ → If Supplier Code might be
└──────────────────────┘   Manufacturer Code → Ask user

STEP 7: CATEGORY ASSIGNMENT
┌──────────────────────┐
│ Auto-categorization  │ → ML-based suggestion
└──────────────────────┘   3-level structure: K1/K2/K3
         ↓
┌──────────────────────┐
│ Confidence Score     │ → If low confidence → Review Queue
└──────────────────────┘

STEP 8: HUMAN REVIEW QUEUE
┌──────────────────────┐
│ Review Triggers      │ → Items needing review:
└──────────────────────┘   • Missing Manufacturer Code
         ↓                 • Low confidence category
         ↓                 • Duplicate suspicion
         ↓                 • Anomalous data
┌──────────────────────┐   • New supplier
│ User Interface       │ → Review screen shows:
└──────────────────────┘   • Product details
         ↓                 • Suggested values
         ↓                 • Confidence scores
┌──────────────────────┐   • Historical context
│ User Actions         │ → Approve / Edit / Reject
└──────────────────────┘
         ↓
┌──────────────────────┐
│ Learning Feedback    │ → Train ML models
└──────────────────────┘   → Update rules

STEP 9: EXPORT
┌──────────────────────┐
│ Export Formats       │ → CSV
└──────────────────────┘   → Excel
         ↓                 → JSON
         ↓                 → XML
┌──────────────────────┐   → API
│ Export Filters       │ → Filter by:
└──────────────────────┘   • Date range
         ↓                 • Supplier
         ↓                 • Category
┌──────────────────────┐   • Review status
│ Use in External      │ → Import to other systems
│ Systems              │   (NO write-back to Pylon)
└──────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS OPERATIONS                         │
└─────────────────────────────────────────────────────────────────┘

• RAG Search: Query supplier agreements for context
• Product Updates: New data from invoices updates existing products
• Rule Management: Add/edit supplier-specific rules
• Performance Monitoring: Track parsing accuracy, review queue size
• Data Quality Reports: Completeness, conflicts, anomalies
```

### 1.3 Βασικές Λειτουργίες

#### 1.3.1 Διαχείριση Προμηθευτών
- **Δημιουργία Supplier Profile:** Όνομα, contact info, default rules
- **Upload Συμφωνητικού:** PDF storage + RAG indexing
- **Configuration Rules:** Supplier-specific parsing & normalization rules
- **Monitoring:** Track invoice volume, data quality per supplier

#### 1.3.2 Διαχείριση Εγγράφων
- **Multi-format Upload:** Drag-and-drop interface
- **Batch Processing:** Upload πολλαπλών αρχείων ταυτόχρονα
- **Format Auto-detection:** Automatic identification of document type
- **Processing Status:** Real-time progress tracking
- **Error Handling:** Failed parsing → Review Queue

#### 1.3.3 Διαχείριση Προϊόντων
- **3-Code System:**
  - **Κωδικός Εργαλύων:** Μοναδικό EDM identifier (auto-generated)
  - **Κωδικός Προμηθευτή:** REQUIRED, used for lookups
  - **Κωδικός Κατασκευαστή:** OPTIONAL, enriched from catalogs/scraping

- **CRUD Operations:**
  - Create: From invoice/manual input
  - Read: Search by any code, description, category
  - Update: With source precedence rules
  - Delete: Soft delete with audit trail

- **Data Enrichment:**
  - Specifications from XML/catalogs
  - Category assignment (ML-assisted)
  - Manufacturer identification
  - Price history tracking

#### 1.3.4 Review Queue
- **Smart Queuing:** Auto-detect items needing review
- **Priority System:** Critical issues first
- **Batch Actions:** Approve/reject multiple items
- **Context Display:** Show all relevant data for decision-making
- **Learning Loop:** User actions improve auto-processing

#### 1.3.5 Export & Reporting
- **Flexible Exports:** Multiple formats (CSV, Excel, JSON, XML)
- **Custom Filters:** Date, supplier, category, status
- **Data Quality Reports:** Completeness metrics, conflict reports
- **Analytics Dashboard:** Volume trends, processing efficiency

### 1.4 Business Rules

#### 1.4.1 Product Identity Rules
```
RULE P1: Κωδικός Προμηθευτή (Supplier Code)
- REQUIRED για κάθε προϊόν
- Used as primary lookup key
- Must be unique per supplier
- Cannot be null/empty

RULE P2: Κωδικός Εργαλύων (Ergalyon Code)
- Auto-generated για νέα προϊόντα
- Format: ERG-XXXXXXXX (8-digit sequential)
- UNIQUE across entire system
- Immutable after creation

RULE P3: Κωδικός Κατασκευαστή (Manufacturer Code)
- OPTIONAL
- Enriched from: Catalogs > XML > Scraping
- If missing: Flag for review
- Special case: If Supplier Code looks like Manufacturer Code
  → Ask user: "Χρησιμοποιήσουμε τον κωδικό προμηθευτή ως κωδικό κατασκευαστή;"

RULE P4: Code Precedence
- When multiple sources provide same code:
  1. Manual user input (highest trust)
  2. XML structured data
  3. Catalog PDF extraction
  4. Web scraping (lowest trust)
- NEVER overwrite higher-quality source with lower-quality
```

#### 1.4.2 Data Update Rules
```
RULE U1: Non-Destructive Updates
- Existing data is KEPT unless explicitly overwritten by user
- New invoice with same product → Update only NEW fields
- Exception: Price always updates (with history tracking)

RULE U2: Source Tracking
- Every field has source metadata: XML | Catalog | Manual | Scraping
- Source timestamp recorded
- Source priority enforced

RULE U3: Conflict Resolution
- If new data conflicts with existing:
  → Check source precedence
  → If same level → Flag for review
  → User decision becomes new manual source

RULE U4: Manufacturer Code Discovery
- If product has Supplier Code but no Manufacturer Code:
  1. Search in uploaded catalogs (by Supplier Code)
  2. If found → Auto-populate
  3. If not found → Try web scraping
  4. If still not found → Review Queue
  5. User can mark "Does not have manufacturer code"
```

#### 1.4.3 Supplier-Specific Rules
```
RULE S1: Rule Engine Architecture
- Each supplier can have custom rules
- Rules applied BEFORE product creation/update
- Rule types:
  • Code normalization (e.g., remove prefixes)
  • Field mapping (custom column names)
  • Validation rules (format checks)
  • Enrichment hints (where to find specs)

RULE S2: Poimenidis-Specific Rules
- Code Normalization: 03-XXXXX → XXXXX
  • Detect "03-" prefix
  • Remove prefix
  • Use XXXXX as Supplier Code
- XML Parsing: Priority over PDF/images
- Invoice Format: Known structure, high confidence parsing
```

#### 1.4.4 Category Assignment Rules
```
RULE C1: 3-Level Hierarchy
- K1 (Category Level 1): Top-level (e.g., "Εργαλεία Χειρός")
- K2 (Category Level 2): Mid-level (e.g., "Πριόνια")
- K3 (Category Level 3): Detailed (e.g., "Σπαθόσεγες")
- Every product must have all 3 levels

RULE C2: Auto-Categorization
- ML model suggests category based on description
- Confidence threshold: 85%
- If < 85% → Review Queue
- User corrections retrain model

RULE C3: Category Inheritance
- If supplier always sends same category items, suggest from history
- Multi-category suppliers: Use description-based ML
```

#### 1.4.5 Review Queue Rules
```
RULE R1: Auto-Trigger Conditions
- Missing Manufacturer Code
- Category confidence < 85%
- Duplicate Supplier Code detection
- Anomalous price (>50% variance from last invoice)
- New supplier (first 50 products always reviewed)
- OCR confidence < 90%

RULE R2: Priority Levels
- CRITICAL: Duplicate detection, validation errors
- HIGH: Missing manufacturer code, low ML confidence
- MEDIUM: Price anomalies, new supplier
- LOW: Enrichment opportunities

RULE R3: Review Resolution
- User must take action: Approve | Edit | Reject
- "Edit" creates Manual source entry
- "Approve" trains ML models positively
- "Reject" sends back to parsing
```

#### 1.4.6 No Pylon Integration
```
RULE N1: EDM is Standalone
- EDM does NOT read from Pylon database
- EDM does NOT write to Pylon database
- Pylon codes are IGNORED by EDM

RULE N2: Export-Only Integration
- EDM exports data in standard formats
- Other systems (including Pylon) can IMPORT EDM data
- No real-time sync
- No bidirectional data flow
```

---

## 2. Domain Model

### 2.1 Core Entities

Το EDM domain model αποτελείται από τις ακόλουθες κύριες οντότητες:

#### Core Business Entities
1. **Product** - Κεντρική οντότητα, αντιπροσωπεύει ένα εργαλείο/προϊόν
2. **Supplier** - Προμηθευτής
3. **Manufacturer** - Κατασκευαστής (derived entity, not always known)
4. **Category** - 3-level category hierarchy (K1/K2/K3)

#### Document Entities
5. **SupplierAgreement** - Συμφωνητικό προμηθευτή (stored in RAG)
6. **Invoice** - Τιμολόγιο
7. **Offer** - Προσφορά
8. **Catalog** - Κατάλογος προϊόντων

#### Transaction Entities
9. **InvoiceItem** - Γραμμή τιμολογίου (links Invoice to Product)
10. **OfferItem** - Γραμμή προσφοράς

#### Processing Entities
11. **ReviewQueueItem** - Item που χρειάζεται human review
12. **ProductSpecification** - Technical specs (key-value pairs)
13. **PriceHistory** - Ιστορικό τιμών
14. **SupplierRule** - Supplier-specific processing rules

#### System Entities
15. **User** - System users
16. **AuditLog** - Change tracking
17. **ProcessingJob** - Batch processing tracking
18. **DataSource** - Metadata about data origin

### 2.2 Entity Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENTITY RELATIONSHIP DIAGRAM                   │
└─────────────────────────────────────────────────────────────────┘

                        ┌──────────────┐
                        │   Supplier   │
                        └──────┬───────┘
                               │ 1
                               │
                   ┌───────────┼────────────┬──────────────┐
                   │           │            │              │
                   │ N         │ N          │ N            │ N
        ┌──────────▼───┐  ┌───▼────────┐  │   ┌─────────▼────────┐
        │SupplierRule  │  │SupplierAg. │  │   │   Invoice        │
        │(code rules)  │  │(RAG stored)│  │   └────────┬─────────┘
        └──────────────┘  └────────────┘  │            │ 1
                                           │            │
                                           │            │ N
                                           │   ┌────────▼─────────┐
                                           │   │  InvoiceItem     │
                                           │   └────────┬─────────┘
                                           │            │ N
                                           │            │
                                           │ N          │ 1
                                      ┌────▼────────────▼────┐
                                      │      Product         │◄────┐
                                      │  (Central Entity)    │     │
                                      └──┬────────┬──────┬───┘     │
                                         │        │      │         │
                        ┌────────────────┘        │      └─────┐   │
                        │ 1                       │ N          │ N │ N
                        │                         │            │   │
                   ┌────▼────────┐      ┌────────▼──────┐  ┌──▼───▼──────┐
                   │  Category   │      │ProductSpec    │  │ReviewQueue  │
                   │  (K1/K2/K3) │      │(key-value)    │  │Item         │
                   └─────────────┘      └───────────────┘  └─────────────┘
                        │ 1
                        │
                        │ N
                   ┌────▼────────┐
                   │Manufacturer │
                   │(optional)   │
                   └─────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    DETAILED RELATIONSHIPS                        │
└─────────────────────────────────────────────────────────────────┘

Product ↔ Supplier
- Relationship: Many-to-Many (product can have multiple suppliers over time)
- Join: InvoiceItem (tracks which supplier provided product on which invoice)
- Key: product.supplier_code + supplier.id uniquely identifies source

Product ↔ Category
- Relationship: Many-to-One
- Every product has exactly 3 levels: K1, K2, K3
- Foreign Keys: product.category_k1_id, category_k2_id, category_k3_id

Product ↔ Manufacturer
- Relationship: Many-to-One (optional)
- manufacturer_id can be NULL
- manufacturer_code can be NULL (enriched later)

Product ↔ ProductSpecification
- Relationship: One-to-Many
- Specs stored as flexible key-value pairs
- Examples: {"Ισχύς": "800W", "Βάρος": "2.5kg", "Τάση": "220V"}

Product ↔ ReviewQueueItem
- Relationship: One-to-Many
- Same product can appear multiple times (different review reasons)
- Once resolved, item marked complete

Invoice ↔ InvoiceItem
- Relationship: One-to-Many
- Invoice is header (date, supplier, total)
- InvoiceItem is line (product, quantity, price)

InvoiceItem ↔ Product
- Relationship: Many-to-One
- InvoiceItem creates or updates Product
- Tracks data source for enrichment

Supplier ↔ SupplierRule
- Relationship: One-to-Many
- Multiple rules per supplier
- Rule types: normalization, validation, enrichment

Supplier ↔ SupplierAgreement
- Relationship: One-to-Many
- Historical agreements stored
- RAG-indexed for search, not validation

Product ↔ PriceHistory
- Relationship: One-to-Many
- Every price change recorded
- Tracks: price, date, supplier, invoice_id
```

### 2.3 Domain Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                    EDM DOMAIN MODEL - HIGH LEVEL                  │
└───────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │    DATA SOURCES     │
                    │  (External World)   │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
   ┌────────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
   │  Agreements     │  │  Invoices   │  │   Catalogs     │
   │  (PDF docs)     │  │ (multi-fmt) │  │  (PDF/Excel)   │
   └────────┬────────┘  └──────┬──────┘  └───────┬────────┘
            │                  │                  │
            │ RAG              │ PARSE            │ EXTRACT
            │                  │                  │
   ┌────────▼────────┐  ┌──────▼──────────────────▼────────┐
   │  RAG Archive    │  │     PROCESSING LAYER             │
   │  (Search only)  │  │  • Format Detection              │
   └─────────────────┘  │  • Parsing (PDF/XML/OCR/Excel)   │
                        │  • Normalization (Rules Engine)  │
                        │  • Validation                     │
                        └──────────────┬───────────────────┘
                                       │
                        ┌──────────────▼───────────────────┐
                        │       PRODUCT DOMAIN             │
                        │                                  │
                        │  ┌─────────────────────┐         │
                        │  │      Product        │         │
                        │  │  ┌───────────────┐  │         │
                        │  │  │ Κωδ. Εργαλύων│  │         │
                        │  │  │ Κωδ. Προμηθευ.│  │         │
                        │  │  │ Κωδ. Κατασκευ.│  │         │
                        │  │  │ Description   │  │         │
                        │  │  │ Specifications│  │         │
                        │  │  │ Category      │  │         │
                        │  │  └───────────────┘  │         │
                        │  └─────────────────────┘         │
                        │           ▲                      │
                        │           │                      │
                        └───────────┼──────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
         ┌──────────▼─────┐  ┌──────▼──────┐  ┌───▼────────────┐
         │  ENRICHMENT    │  │   REVIEW    │  │   EXPORT       │
         │  • XML data    │  │   QUEUE     │  │  • CSV/Excel   │
         │  • Catalogs    │  │  • Human    │  │  • JSON/XML    │
         │  • Manual      │  │    Review   │  │  • API         │
         │  • Scraping    │  │  • Learning │  │                │
         └────────────────┘  └─────────────┘  └────────────────┘
```

---

*[Η συνέχεια του document θα παρέχεται σε επόμενο τμήμα λόγω μεγέθους]*

## 3. Entity Definitions

### 3.1 Product

**Κεντρική οντότητα του συστήματος**. Αντιπροσωπεύει ένα εργαλείο/προϊόν.

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `ergalyon_code` | VARCHAR(50) | Yes | Κωδικός Εργαλύων - Auto-generated, unique, format: ERG-XXXXXXXX |
| `supplier_code` | VARCHAR(100) | Yes | Κωδικός Προμηθευτή - REQUIRED, used for lookups |
| `manufacturer_code` | VARCHAR(100) | No | Κωδικός Κατασκευαστή - Optional, enriched |
| `supplier_id` | UUID | Yes | Foreign key to Supplier |
| `manufacturer_id` | UUID | No | Foreign key to Manufacturer (optional) |
| `description` | TEXT | Yes | Product description (from invoice) |
| `description_normalized` | TEXT | Yes | Cleaned/normalized description for search |
| `category_k1_id` | UUID | No | Category Level 1 |
| `category_k2_id` | UUID | No | Category Level 2 |
| `category_k3_id` | UUID | No | Category Level 3 |
| `category_confidence` | DECIMAL(5,2) | No | ML confidence score (0-100) |
| `current_price` | DECIMAL(10,2) | No | Latest price |
| `price_currency` | VARCHAR(3) | No | EUR, USD, etc. |
| `image_url` | TEXT | No | Product image (from catalog or scraped) |
| `barcode` | VARCHAR(50) | No | EAN/UPC if available |
| `manufacturer_flag` | BOOLEAN | No | Flag: "Supplier code might be manufacturer code" |
| `data_completeness_score` | INTEGER | No | 0-100, how complete is the data |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |
| `updated_at` | TIMESTAMP | Yes | Last update timestamp |
| `created_by` | UUID | No | User who created (NULL if auto) |
| `updated_by` | UUID | No | User who last updated |

**Note:** Λόγω του μεγέθους του πλήρους specification document (~12,000+ γραμμές), έχω δημιουργήσει το πρώτο τμήμα με τις ενότητες 1-2 και την αρχή της ενότητας 3.

Μπορώ να συνεχίσω την προσθήκη του υπόλοιπου περιεχομένου εάν το επιθυμείτε, ή μπορείτε να χρησιμοποιήσετε αυτό το αρχείο ως template και να το επεκτείνετε σταδιακά με βάση τις πληροφορίες από τα uploaded documents και τη συζήτηση σας.

Θέλετε να συνεχίσω με την πλήρη ενότητα 3 και τις υπόλοιπες ενότητες;
