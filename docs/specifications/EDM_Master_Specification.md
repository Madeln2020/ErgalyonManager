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

#### Indexes & Constraints (Product)
- `UNIQUE(ergalyon_code)` — global uniqueness
- `UNIQUE(supplier_id, supplier_code)` — ένας supplier code ανά προμηθευτή
- `INDEX(description_normalized)` — full-text search
- `INDEX(category_k1_id, category_k2_id, category_k3_id)` — category filtering

---

### 3.2 Supplier

Αντιπροσωπεύει έναν προμηθευτή εργαλείων.

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `name` | VARCHAR(255) | Yes | Επωνυμία προμηθευτή |
| `vat_number` | VARCHAR(20) | No | ΑΦΜ |
| `country` | VARCHAR(2) | No | ISO country code (default: GR) |
| `contact_email` | VARCHAR(255) | No | Email επικοινωνίας |
| `contact_phone` | VARCHAR(50) | No | Τηλέφωνο |
| `rules_json` | JSONB | No | Supplier-specific rules (βλ. §8) |
| `default_category_k1_id` | UUID | No | Default κατηγορία αν ο supplier είναι single-category |
| `parsing_profile` | VARCHAR(50) | No | Προτεινόμενος parser (xml/pdf_structured/ocr) |
| `is_active` | BOOLEAN | Yes | Ενεργός προμηθευτής (default: true) |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |
| `updated_at` | TIMESTAMP | Yes | Last update timestamp |

**Note:** Το `rules_json` περιέχει το πλήρες rule set που εφαρμόζει το Supplier Rule Engine (§8). Παράδειγμα Poimenidis: `{"code_normalization": [{"type": "strip_prefix", "prefix": "03-"}]}`.

---

### 3.3 Invoice

Header οντότητα τιμολογίου/προσφοράς.

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `supplier_id` | UUID | Yes | Foreign key to Supplier |
| `document_type` | VARCHAR(20) | Yes | invoice / offer / catalog |
| `invoice_number` | VARCHAR(100) | No | Αριθμός παραστατικού |
| `invoice_date` | DATE | No | Ημερομηνία παραστατικού |
| `file_path` | TEXT | Yes | Path του original αρχείου (storage) |
| `file_format` | VARCHAR(20) | Yes | xml / pdf / image / excel |
| `status` | VARCHAR(30) | Yes | Lifecycle status (βλ. §4.1) |
| `parsed_data_json` | JSONB | No | Raw parsed output πριν normalization |
| `parsing_confidence` | DECIMAL(5,2) | No | Overall confidence (0-100) |
| `total_amount` | DECIMAL(12,2) | No | Συνολικό ποσό |
| `currency` | VARCHAR(3) | No | EUR, USD, etc. |
| `error_message` | TEXT | No | Μήνυμα σφάλματος αν status=failed |
| `created_at` | TIMESTAMP | Yes | Upload timestamp |
| `processed_at` | TIMESTAMP | No | Ολοκλήρωση processing |

**Status values:** `uploaded → parsing → parsed → normalized → enriched → reviewed → exported` (βλ. §4.2 για state transitions). Επιπλέον: `failed`.

---

### 3.4 InvoiceItem

Γραμμή τιμολογίου — συνδέει το Invoice με ένα Product.

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `invoice_id` | UUID | Yes | Foreign key to Invoice |
| `product_id` | UUID | No | Foreign key to Product (NULL μέχρι το matching) |
| `line_number` | INTEGER | No | Σειρά στη γραμμή τιμολογίου |
| `raw_supplier_code` | VARCHAR(100) | No | Κωδικός όπως εμφανίζεται πριν normalization |
| `normalized_supplier_code` | VARCHAR(100) | No | Μετά την εφαρμογή των rules |
| `raw_description` | TEXT | Yes | Περιγραφή από το παραστατικό |
| `quantity` | DECIMAL(10,3) | No | Ποσότητα |
| `unit_price` | DECIMAL(10,2) | No | Τιμή μονάδας |
| `line_total` | DECIMAL(12,2) | No | Σύνολο γραμμής |
| `vat_rate` | DECIMAL(5,2) | No | Συντελεστής ΦΠΑ |
| `match_confidence` | DECIMAL(5,2) | No | Confidence του product matching |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |

---

### 3.5 SupplierAgreement

Συμφωνητικό προμηθευτή — αποθηκεύεται **μόνο για RAG/Archive**, ΟΧΙ για validation/comparison (βλ. Out of Scope).

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `supplier_id` | UUID | Yes | Foreign key to Supplier |
| `title` | VARCHAR(255) | No | Τίτλος/περιγραφή συμφωνητικού |
| `file_path` | TEXT | Yes | Path του original εγγράφου |
| `valid_from` | DATE | No | Έναρξη ισχύος |
| `valid_to` | DATE | No | Λήξη ισχύος |
| `rag_index_id` | VARCHAR(100) | No | Reference στο vector store (chunk collection) |
| `indexed_at` | TIMESTAMP | No | Πότε έγινε το RAG indexing |
| `created_at` | TIMESTAMP | Yes | Upload timestamp |

**Note:** Το EDM **δεν** συγκρίνει τα συμφωνητικά με τα τιμολόγια. Χρησιμοποιούνται αποκλειστικά για semantic search (π.χ. «ποια ήταν η συμφωνημένη έκπτωση;»).

---

### 3.6 Category

3-level ιεραρχία κατηγοριών (K1/K2/K3).

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `level` | INTEGER | Yes | 1, 2, ή 3 |
| `name` | VARCHAR(255) | Yes | Όνομα κατηγορίας (π.χ. "Πριόνια") |
| `parent_id` | UUID | No | Foreign key to Category (NULL για level 1) |
| `code` | VARCHAR(50) | No | Internal category code |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |

**Constraint:** `parent_id` πρέπει να δείχνει σε κατηγορία ένα επίπεδο πάνω (level N → level N-1). Level 1 έχει `parent_id = NULL`.

---

### 3.7 ProductSpecification

Technical specs ως flexible key-value pairs.

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `product_id` | UUID | Yes | Foreign key to Product |
| `spec_key` | VARCHAR(100) | Yes | π.χ. "Ισχύς", "Βάρος", "Τάση" |
| `spec_value` | VARCHAR(255) | Yes | π.χ. "800W", "2.5kg", "220V" |
| `unit` | VARCHAR(20) | No | Μονάδα μέτρησης |
| `source` | VARCHAR(20) | Yes | xml / catalog / manual / scraping |
| `source_confidence` | DECIMAL(5,2) | No | Confidence της εξαγωγής |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |

**Constraint:** `UNIQUE(product_id, spec_key)` — μία τιμή ανά spec key (η νεότερη/υψηλότερης προτεραιότητας πηγή υπερισχύει).

---

### 3.8 ReviewQueueItem

Item που χρειάζεται human review (βλ. §7 για πλήρη specification).

#### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Primary key |
| `product_id` | UUID | No | Foreign key to Product (αν αφορά προϊόν) |
| `invoice_item_id` | UUID | No | Foreign key to InvoiceItem (αν αφορά γραμμή) |
| `review_type` | VARCHAR(50) | Yes | low_confidence / duplicate / missing_manufacturer_code / price_anomaly / new_supplier |
| `priority` | VARCHAR(20) | Yes | CRITICAL / HIGH / MEDIUM / LOW |
| `status` | VARCHAR(20) | Yes | open / in_progress / resolved / dismissed |
| `payload_json` | JSONB | No | Context data (suggested values, confidence scores) |
| `prompt_text` | TEXT | No | Ερώτηση προς τον χρήστη |
| `resolution` | VARCHAR(50) | No | approved / edited / rejected |
| `resolved_by` | UUID | No | User που έλυσε το item |
| `resolved_at` | TIMESTAMP | No | Χρόνος επίλυσης |
| `created_at` | TIMESTAMP | Yes | Record creation timestamp |


---

## 4. Event Specification

Το EDM είναι event-driven: κάθε σημαντική αλλαγή κατάστασης (state transition) εκπέμπει ένα event που μπορεί να ενεργοποιήσει async tasks (Celery), audit logging και review triggers.

### 4.1 Lifecycle Events

#### 4.1.1 Invoice Lifecycle Events

Το `Invoice.status` ακολουθεί μια αυστηρή ροή. Κάθε μετάβαση εκπέμπει event:

| Event | Από → Προς | Trigger | Side effects |
|-------|-----------|---------|--------------|
| `invoice.uploaded` | (new) → `uploaded` | Χρήστης ανεβάζει αρχείο | Αποθήκευση file, format detection, enqueue parsing |
| `invoice.parsing_started` | `uploaded` → `parsing` | Worker αναλαμβάνει το job | Lock invoice, route σε parser (§9) |
| `invoice.parsed` | `parsing` → `parsed` | Επιτυχής εξαγωγή | Δημιουργία InvoiceItems, αποθήκευση `parsed_data_json` |
| `invoice.parse_failed` | `parsing` → `failed` | Σφάλμα/χαμηλό confidence | Set `error_message`, δημιουργία ReviewQueueItem |
| `invoice.normalized` | `parsed` → `normalized` | Εφαρμογή Supplier Rules (§8) | Συμπλήρωση `normalized_supplier_code` ανά item |
| `invoice.enriched` | `normalized` → `enriched` | Ολοκλήρωση enrichment (§1.2 STEP 6) | Update Products, ProductSpecifications |
| `invoice.reviewed` | `enriched` → `reviewed` | Όλα τα σχετικά ReviewQueueItems resolved | Mark ready for export |
| `invoice.exported` | `reviewed` → `exported` | Export job ολοκληρώθηκε | Audit log entry |

```
┌──────────┐  uploaded   ┌─────────┐  parsing   ┌────────┐
│ (upload) │────────────▶│ parsing │───────────▶│ parsed │
└──────────┘             └────┬────┘            └───┬────┘
                              │ parse_failed        │ normalize
                              ▼                     ▼
                         ┌────────┐           ┌────────────┐
                         │ failed │           │ normalized │
                         └────────┘           └─────┬──────┘
                                                    │ enrich
                                                    ▼
   ┌──────────┐  export  ┌──────────┐  review  ┌──────────┐
   │ exported │◀─────────│ reviewed │◀─────────│ enriched │
   └──────────┘          └──────────┘          └──────────┘
```

#### 4.1.2 Product Lifecycle Events

| Event | Trigger | Payload | Side effects |
|-------|---------|---------|--------------|
| `product.created` | Νέος supplier_code που δεν υπάρχει | `{product_id, supplier_id, supplier_code}` | Auto-generate Ergalyon code (ERG-XXXXXXXX) |
| `product.updated` | Νέα δεδομένα για υπάρχον product | `{product_id, changed_fields, source}` | Source precedence check (§1.4.1 P4) |
| `product.price_changed` | Νέα τιμή σε invoice | `{product_id, old_price, new_price}` | Insert PriceHistory record |
| `product.enriched` | Νέα specs/manufacturer code | `{product_id, source, fields}` | Update data_completeness_score |
| `product.categorized` | ML category assignment | `{product_id, k1, k2, k3, confidence}` | Αν confidence < 85% → review |
| `product.flagged` | Supplier code μοιάζει με manufacturer code | `{product_id}` | Set `manufacturer_flag=true`, review |
| `product.deleted` | Soft delete | `{product_id, deleted_by}` | Audit log, set deleted_at |

#### 4.1.3 Supplier Rule Application Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `rule.applied` | Κανόνας εφαρμόστηκε σε item | `{rule_id, rule_type, input, output}` |
| `rule.skipped` | Κανόνας δεν ταίριαξε | `{rule_id, reason}` |
| `rule.conflict` | Δύο rules παράγουν διαφορετικό αποτέλεσμα | `{rule_ids, item_id}` → review |
| `rule.created` | Νέος κανόνας προστέθηκε σε supplier | `{supplier_id, rule_id}` |
| `rule.updated` | Τροποποίηση κανόνα | `{supplier_id, rule_id, diff}` |

#### 4.1.4 Review Queue Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `review.created` | Auto-trigger condition (§7.1) | `{review_id, review_type, priority}` |
| `review.assigned` | Χρήστης αναλαμβάνει item | `{review_id, user_id}` |
| `review.resolved` | Approve/Edit/Reject | `{review_id, resolution, user_id}` |
| `review.dismissed` | Item κρίθηκε μη σχετικό | `{review_id, reason}` |
| `review.escalated` | Item ανοιχτό > SLA | `{review_id}` → priority bump |

### 4.2 State Transitions

#### Invoice State Machine (formal)

```
States: {uploaded, parsing, parsed, normalized, enriched, reviewed, exported, failed}
Initial: uploaded
Terminal: exported, failed

Allowed transitions:
  uploaded   → parsing | failed
  parsing    → parsed | failed
  parsed     → normalized | failed
  normalized → enriched | failed
  enriched   → reviewed
  reviewed   → exported | enriched   (re-enrich αν χρειαστεί)
  failed     → parsing                (retry μετά από manual fix)

Guards:
  - parsed → normalized: requires supplier.rules_json loaded
  - enriched → reviewed: requires ALL open ReviewQueueItems(invoice) == 0
  - reviewed → exported: requires user-initiated OR scheduled export
```

#### ReviewQueueItem State Machine

```
States: {open, in_progress, resolved, dismissed}
Initial: open
Terminal: resolved, dismissed

  open        → in_progress | dismissed
  in_progress → resolved | open        (release χωρίς resolution)
  resolved    → (terminal)
  dismissed   → (terminal)
```

### 4.3 Event Handlers

Οι handlers υλοποιούνται ως Celery tasks. Κάθε event publish γίνεται μέσω Redis pub/sub.

```python
# Παράδειγμα event handler (pseudo-code)

@on_event("invoice.parsed")
def handle_invoice_parsed(event):
    invoice = get_invoice(event.invoice_id)
    # 1. Trigger normalization (apply supplier rules §8)
    enqueue("normalize_invoice", invoice.id)

@on_event("product.flagged")
def handle_product_flagged(event):
    # Δημιουργία review item με το συγκεκριμένο prompt
    create_review_item(
        product_id=event.product_id,
        review_type="missing_manufacturer_code",
        priority="HIGH",
        prompt_text="Θα χρησιμοποιηθεί ο κωδικός προμηθευτή ως κωδικός κατασκευαστή;"
    )

@on_event("product.price_changed")
def handle_price_changed(event):
    insert_price_history(event.product_id, event.new_price)
    if abs(event.new_price - event.old_price) / event.old_price > 0.5:
        create_review_item(product_id=event.product_id,
                           review_type="price_anomaly", priority="MEDIUM")
```

**Event delivery guarantees:**
- At-least-once delivery (idempotent handlers)
- Failed handlers → retry με exponential backoff (max 3)
- Dead-letter queue για permanently failed events
- Όλα τα events καταγράφονται στο AuditLog


---

## 5. Database Design

### 5.1 Schema Overview

Η βάση δεδομένων είναι **PostgreSQL 15+**. Χρησιμοποιεί `UUID` primary keys (`gen_random_uuid()`), `JSONB` για flexible/semi-structured data, και `TIMESTAMPTZ` για όλα τα timestamps.

```
┌─────────────────────────────────────────────────────────────────┐
│                    EDM DATABASE SCHEMA (overview)                │
└─────────────────────────────────────────────────────────────────┘

  suppliers ──1:N──┬── supplier_rules
                   ├── supplier_agreements
                   └── invoices ──1:N── invoice_items ──N:1── products
                                                                  │
  categories (self-ref K1/K2/K3) ──┐                             │
                                    └──N:1────────────────────────┤
                                                                  ├── product_specifications
                                                                  ├── product_source_data
                                                                  ├── price_history
                                                                  └── review_queue
```

**Extensions:**
```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- trigram search σε descriptions
CREATE EXTENSION IF NOT EXISTS "vector";      -- (προαιρετικό) RAG embeddings
```

### 5.2 Table Definitions

#### 5.2.1 suppliers

```sql
CREATE TABLE suppliers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    VARCHAR(255) NOT NULL,
    vat_number              VARCHAR(20),
    country                 VARCHAR(2) NOT NULL DEFAULT 'GR',
    contact_email           VARCHAR(255),
    contact_phone           VARCHAR(50),
    rules_json              JSONB NOT NULL DEFAULT '{}'::jsonb,
    default_category_k1_id  UUID REFERENCES categories(id),
    parsing_profile         VARCHAR(50),
    is_active               BOOLEAN NOT NULL DEFAULT true,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_supplier_vat UNIQUE (vat_number)
);
```

#### 5.2.2 categories

```sql
CREATE TABLE categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level       SMALLINT NOT NULL CHECK (level IN (1, 2, 3)),
    name        VARCHAR(255) NOT NULL,
    parent_id   UUID REFERENCES categories(id) ON DELETE RESTRICT,
    code        VARCHAR(50),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_level1_no_parent
        CHECK ((level = 1 AND parent_id IS NULL) OR (level > 1 AND parent_id IS NOT NULL))
);
```

#### 5.2.3 products

```sql
CREATE TABLE products (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ergalyon_code            VARCHAR(50) NOT NULL,
    supplier_code            VARCHAR(100) NOT NULL,
    manufacturer_code        VARCHAR(100),
    ean                      VARCHAR(50),
    supplier_id              UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    manufacturer_id          UUID,
    description              TEXT NOT NULL,
    description_normalized   TEXT NOT NULL,
    specs_json               JSONB NOT NULL DEFAULT '{}'::jsonb,
    category_k1_id           UUID REFERENCES categories(id),
    category_k2_id           UUID REFERENCES categories(id),
    category_k3_id           UUID REFERENCES categories(id),
    category_confidence      DECIMAL(5,2),
    current_price            DECIMAL(10,2),
    price_currency           VARCHAR(3),
    image_url                TEXT,
    manufacturer_flag        BOOLEAN NOT NULL DEFAULT false,
    data_completeness_score  SMALLINT CHECK (data_completeness_score BETWEEN 0 AND 100),
    is_deleted               BOOLEAN NOT NULL DEFAULT false,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by               UUID,
    updated_by               UUID,
    CONSTRAINT uq_ergalyon_code UNIQUE (ergalyon_code),
    CONSTRAINT uq_supplier_code UNIQUE (supplier_id, supplier_code)
);
```

> **Note:** Το `specs_json` κρατά ένα denormalized snapshot των specs για γρήγορα reads· η κανονική (normalized) πηγή αλήθειας είναι ο πίνακας `product_specifications`.

#### 5.2.4 invoices

```sql
CREATE TABLE invoices (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id         UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    document_type       VARCHAR(20) NOT NULL DEFAULT 'invoice'
                          CHECK (document_type IN ('invoice','offer','catalog')),
    invoice_number      VARCHAR(100),
    invoice_date        DATE,
    file_path           TEXT NOT NULL,
    file_format         VARCHAR(20) NOT NULL
                          CHECK (file_format IN ('xml','pdf','image','excel')),
    status              VARCHAR(30) NOT NULL DEFAULT 'uploaded'
                          CHECK (status IN ('uploaded','parsing','parsed','normalized',
                                            'enriched','reviewed','exported','failed')),
    parsed_data_json    JSONB,
    parsing_confidence  DECIMAL(5,2),
    total_amount        DECIMAL(12,2),
    currency            VARCHAR(3) DEFAULT 'EUR',
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at        TIMESTAMPTZ
);
```

#### 5.2.5 invoice_items

```sql
CREATE TABLE invoice_items (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id                UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id                UUID REFERENCES products(id) ON DELETE SET NULL,
    line_number               INTEGER,
    raw_supplier_code         VARCHAR(100),
    normalized_supplier_code  VARCHAR(100),
    raw_description           TEXT NOT NULL,
    quantity                  DECIMAL(10,3),
    unit_price                DECIMAL(10,2),
    line_total                DECIMAL(12,2),
    vat_rate                  DECIMAL(5,2),
    match_confidence          DECIMAL(5,2),
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 5.2.6 product_source_data

Παρακολούθηση data precedence (XML > Catalog > Manual > Scraping) ανά πεδίο.

```sql
CREATE TABLE product_source_data (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id        UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    field_name        VARCHAR(100) NOT NULL,
    field_value       TEXT,
    source            VARCHAR(20) NOT NULL
                        CHECK (source IN ('xml','catalog','manual','scraping')),
    source_priority   SMALLINT NOT NULL,   -- 1=manual, 2=xml, 3=catalog, 4=scraping
    source_ref        TEXT,                -- invoice_id ή URL
    confidence        DECIMAL(5,2),
    is_active         BOOLEAN NOT NULL DEFAULT true,  -- η τρέχουσα winning value
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_active_field
        EXCLUDE (product_id WITH =, field_name WITH =) WHERE (is_active)
);
```

> Το `EXCLUDE` constraint εγγυάται ότι υπάρχει το πολύ **μία active value** ανά (product, field). Όταν έρχεται νέα τιμή υψηλότερης προτεραιότητας, η παλιά γίνεται `is_active=false` (διατήρηση ιστορικού — RULE U1/U2).

#### 5.2.7 product_specifications

```sql
CREATE TABLE product_specifications (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id         UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    spec_key           VARCHAR(100) NOT NULL,
    spec_value         VARCHAR(255) NOT NULL,
    unit               VARCHAR(20),
    source             VARCHAR(20) NOT NULL
                         CHECK (source IN ('xml','catalog','manual','scraping')),
    source_confidence  DECIMAL(5,2),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_product_spec UNIQUE (product_id, spec_key)
);
```

#### 5.2.8 price_history

```sql
CREATE TABLE price_history (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id   UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price        DECIMAL(10,2) NOT NULL,
    currency     VARCHAR(3) NOT NULL DEFAULT 'EUR',
    supplier_id  UUID REFERENCES suppliers(id),
    invoice_id   UUID REFERENCES invoices(id),
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 5.2.9 supplier_rules

> Οι κανόνες αποθηκεύονται **και** ως κανονικοποιημένος πίνακας (audit/versioning) **και** denormalized στο `suppliers.rules_json` για γρήγορη φόρτωση από το engine.

```sql
CREATE TABLE supplier_rules (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id  UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    rule_type    VARCHAR(50) NOT NULL
                   CHECK (rule_type IN ('code_normalization','field_mapping',
                                        'validation','enrichment_hint')),
    config_json  JSONB NOT NULL,
    priority     SMALLINT NOT NULL DEFAULT 100,  -- χαμηλότερο = πρώτο
    is_active    BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 5.2.10 supplier_agreements

```sql
CREATE TABLE supplier_agreements (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id   UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    title         VARCHAR(255),
    file_path     TEXT NOT NULL,
    valid_from    DATE,
    valid_to      DATE,
    rag_index_id  VARCHAR(100),
    indexed_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 5.2.11 review_queue

```sql
CREATE TABLE review_queue (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id       UUID REFERENCES products(id) ON DELETE CASCADE,
    invoice_item_id  UUID REFERENCES invoice_items(id) ON DELETE CASCADE,
    review_type      VARCHAR(50) NOT NULL
                       CHECK (review_type IN ('low_confidence','duplicate',
                              'missing_manufacturer_code','price_anomaly','new_supplier')),
    priority         VARCHAR(20) NOT NULL
                       CHECK (priority IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    status           VARCHAR(20) NOT NULL DEFAULT 'open'
                       CHECK (status IN ('open','in_progress','resolved','dismissed')),
    payload_json     JSONB,
    prompt_text      TEXT,
    resolution       VARCHAR(50) CHECK (resolution IN ('approved','edited','rejected')),
    resolved_by      UUID,
    resolved_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 5.2.12 audit_log

```sql
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id   UUID NOT NULL,
    event_name  VARCHAR(100) NOT NULL,
    payload     JSONB,
    user_id     UUID,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 5.3 Indexes

```sql
-- Products: γρήγορα lookups & search
CREATE INDEX idx_products_supplier        ON products(supplier_id);
CREATE INDEX idx_products_supplier_code   ON products(supplier_id, supplier_code);
CREATE INDEX idx_products_manufacturer    ON products(manufacturer_code);
CREATE INDEX idx_products_ean             ON products(ean);
CREATE INDEX idx_products_categories      ON products(category_k1_id, category_k2_id, category_k3_id);
CREATE INDEX idx_products_desc_trgm       ON products USING gin (description_normalized gin_trgm_ops);
CREATE INDEX idx_products_specs_gin       ON products USING gin (specs_json);

-- Invoices & items
CREATE INDEX idx_invoices_supplier_status ON invoices(supplier_id, status);
CREATE INDEX idx_invoice_items_invoice    ON invoice_items(invoice_id);
CREATE INDEX idx_invoice_items_product    ON invoice_items(product_id);

-- Review queue: dashboard queries (open items by priority)
CREATE INDEX idx_review_open_priority     ON review_queue(status, priority)
    WHERE status IN ('open','in_progress');

-- Price history
CREATE INDEX idx_price_history_product    ON price_history(product_id, recorded_at DESC);

-- Source data precedence
CREATE INDEX idx_source_active            ON product_source_data(product_id, field_name)
    WHERE is_active;
```

### 5.4 Constraints

**Foreign Keys & Referential Integrity (σύνοψη):**

| Child | Parent | On Delete | Σημείωση |
|-------|--------|-----------|----------|
| `products.supplier_id` | `suppliers.id` | RESTRICT | Δεν διαγράφεται supplier με προϊόντα |
| `products.category_kN_id` | `categories.id` | (default) | 3 ξεχωριστά FK |
| `invoices.supplier_id` | `suppliers.id` | RESTRICT | |
| `invoice_items.invoice_id` | `invoices.id` | CASCADE | Διαγραφή invoice → items |
| `invoice_items.product_id` | `products.id` | SET NULL | Διατήρηση γραμμής |
| `product_source_data.product_id` | `products.id` | CASCADE | |
| `product_specifications.product_id` | `products.id` | CASCADE | |
| `price_history.product_id` | `products.id` | CASCADE | |
| `review_queue.product_id` | `products.id` | CASCADE | |
| `supplier_rules.supplier_id` | `suppliers.id` | CASCADE | |
| `supplier_agreements.supplier_id` | `suppliers.id` | CASCADE | |
| `categories.parent_id` | `categories.id` | RESTRICT | Δενδρική ιεραρχία |

**Business constraints (enforced):**
- `UNIQUE(ergalyon_code)` — global
- `UNIQUE(supplier_id, supplier_code)` — ένας κωδικός ανά προμηθευτή (RULE P1)
- `UNIQUE(product_id, spec_key)` — μία spec value ανά key
- `EXCLUDE` σε `product_source_data` — μία active value ανά (product, field)
- `CHECK` σε όλα τα status/enum πεδία
- Soft delete μέσω `products.is_deleted` (RULE — audit trail)


---

## 6. API Contracts

REST API υλοποιημένο με **FastAPI**. Base path: `/api/v1`. Content-Type: `application/json` (εκτός uploads → `multipart/form-data`). Authentication: Bearer JWT.

### 6.1 REST Endpoints

| Method | Path | Σκοπός |
|--------|------|--------|
| POST | `/suppliers` | Δημιουργία προμηθευτή |
| GET | `/suppliers` | Λίστα προμηθευτών |
| GET | `/suppliers/{id}` | Λεπτομέρειες προμηθευτή |
| PUT | `/suppliers/{id}` | Ενημέρωση προμηθευτή/rules |
| POST | `/suppliers/{id}/agreement` | Upload συμφωνητικού (RAG) |
| POST | `/invoices/upload` | Upload τιμολογίου/προσφοράς |
| GET | `/invoices/{id}` | Status & metadata τιμολογίου |
| GET | `/invoices/{id}/items` | Parsed γραμμές τιμολογίου |
| GET | `/products` | Search/list προϊόντων |
| GET | `/products/{id}` | Λεπτομέρειες προϊόντος |
| PUT | `/products/{id}` | Ενημέρωση προϊόντος (manual override) |
| POST | `/products/{id}/enrich` | Trigger enrichment/scraping |
| GET | `/review-queue` | Items προς review |
| POST | `/review-queue/{id}/resolve` | Επίλυση review item |
| GET | `/export` | Export δεδομένων |

### 6.2 Request/Response Formats

#### POST /suppliers
```http
POST /api/v1/suppliers
Content-Type: application/json

{
  "name": "Ποιμενίδης Α.Ε.",
  "vat_number": "094xxxxxx",
  "country": "GR",
  "parsing_profile": "xml",
  "rules_json": {
    "code_normalization": [{ "type": "strip_prefix", "prefix": "03-" }]
  }
}
```
**201 Created**
```json
{ "id": "8f1c...", "name": "Ποιμενίδης Α.Ε.", "is_active": true, "created_at": "2026-06-10T10:00:00Z" }
```

#### POST /suppliers/{id}/agreement
```http
POST /api/v1/suppliers/8f1c.../agreement
Content-Type: multipart/form-data

file=<binary>, title="Συμφωνητικό 2026", valid_from=2026-01-01
```
**202 Accepted** — indexing async
```json
{ "id": "a2b3...", "supplier_id": "8f1c...", "status": "indexing", "rag_index_id": null }
```

#### POST /invoices/upload
```http
POST /api/v1/invoices/upload
Content-Type: multipart/form-data

supplier_id=8f1c..., document_type=invoice, files=<binary[]>
```
**202 Accepted**
```json
{
  "invoices": [
    { "id": "c4d5...", "file_format": "xml", "status": "uploaded" }
  ],
  "job_id": "job_77a1"
}
```

#### GET /invoices/{id}/items
**200 OK**
```json
{
  "invoice_id": "c4d5...",
  "status": "normalized",
  "items": [
    {
      "id": "e6f7...",
      "line_number": 1,
      "raw_supplier_code": "03-12345",
      "normalized_supplier_code": "12345",
      "raw_description": "ΣΕΓΑ ΣΠΑΘΟΥ 800W",
      "quantity": 2,
      "unit_price": 89.90,
      "match_confidence": 92.5,
      "product_id": "p100..."
    }
  ]
}
```

#### PUT /products/{id}
Manual override — δημιουργεί `source=manual` (υψηλότερη προτεραιότητα, RULE P4).
```http
PUT /api/v1/products/p100...
Content-Type: application/json

{
  "manufacturer_code": "BOSCH-2607",
  "category_k1_id": "k1...", "category_k2_id": "k2...", "category_k3_id": "k3...",
  "specs": [{ "spec_key": "Ισχύς", "spec_value": "800", "unit": "W" }]
}
```
**200 OK** — επιστρέφει το ενημερωμένο product με `updated_at` & `data_completeness_score`.

#### GET /review-queue
Query params: `status`, `priority`, `review_type`, `limit`, `offset`.
```http
GET /api/v1/review-queue?status=open&priority=HIGH&limit=20
```
**200 OK**
```json
{
  "total": 42,
  "items": [
    {
      "id": "r1...",
      "review_type": "missing_manufacturer_code",
      "priority": "HIGH",
      "product_id": "p100...",
      "prompt_text": "Θα χρησιμοποιηθεί ο κωδικός προμηθευτή ως κωδικός κατασκευαστή;",
      "payload": { "supplier_code": "12345", "suggestions": [] }
    }
  ]
}
```

#### POST /review-queue/{id}/resolve
```http
POST /api/v1/review-queue/r1.../resolve
Content-Type: application/json

{
  "resolution": "edited",
  "data": { "use_supplier_code_as_manufacturer": true }
}
```
**200 OK**
```json
{ "id": "r1...", "status": "resolved", "resolution": "edited", "resolved_at": "2026-06-10T10:30:00Z" }
```

#### POST /products/{id}/enrich
```http
POST /api/v1/products/p100.../enrich
Content-Type: application/json

{ "sources": ["catalog", "scraping"], "force": false }
```
**202 Accepted**
```json
{ "product_id": "p100...", "job_id": "enr_55", "status": "queued" }
```

#### GET /export
Query params: `format` (csv|excel|json|xml), `supplier_id`, `category_k1_id`, `date_from`, `date_to`, `review_status`.
```http
GET /api/v1/export?format=csv&supplier_id=8f1c...&date_from=2026-01-01
```
**200 OK** — `Content-Type: text/csv` (attachment) ή για μεγάλα datasets **202** με `job_id` & download URL.

### 6.3 Error Handling

Όλα τα errors ακολουθούν ενιαία δομή (RFC 7807-style):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "supplier_code is required",
    "details": [{ "field": "supplier_code", "issue": "missing" }],
    "request_id": "req_abc123"
  }
}
```

| HTTP Status | Code | Πότε |
|-------------|------|------|
| 400 | `VALIDATION_ERROR` | Λανθασμένο/ελλιπές input |
| 401 | `UNAUTHORIZED` | Missing/invalid JWT |
| 403 | `FORBIDDEN` | Ανεπαρκή δικαιώματα |
| 404 | `NOT_FOUND` | Entity δεν βρέθηκε |
| 409 | `CONFLICT` | Duplicate (π.χ. `supplier_code` υπάρχει) |
| 422 | `UNPROCESSABLE` | Parse failed / business rule violation |
| 429 | `RATE_LIMITED` | Πάρα πολλά requests |
| 500 | `INTERNAL_ERROR` | Server error (logged με `request_id`) |
| 503 | `SERVICE_UNAVAILABLE` | Worker/queue down |

**Σημειώσεις:**
- Async endpoints (upload, enrich, export μεγάλων datasets) επιστρέφουν `202` + `job_id`. Polling μέσω `GET /jobs/{job_id}`.
- Rate limiting: 100 req/min ανά API key (configurable).
- Pagination: `limit`/`offset` με `total` count σε όλα τα list endpoints.


---

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

## 9. Parsing Strategy

Το EDM υποστηρίζει πολλαπλές μορφές εγγράφων. Κάθε μορφή δρομολογείται στον κατάλληλο parser με βάση το `file_format` (auto-detection) και το `supplier.parsing_profile`. Κάθε parser επιστρέφει structured output **και** ένα `parsing_confidence` score.

### 9.1 Multi-Format Support

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARSER ROUTING                                │
└─────────────────────────────────────────────────────────────────┘

   Uploaded file
        │
        ▼
  ┌──────────────┐
  │ Format Detect│  (extension + MIME + content sniff)
  └──────┬───────┘
         │
   ┌─────┼─────────┬──────────┬───────────┬──────────────┐
   ▼     ▼         ▼          ▼           ▼              ▼
 XML   PDF       PDF        Image      Catalog        Excel
(myDATA) (structured) (scanned)  (JPG/PNG)    PDF        (xlsx/csv)
   │     │         │          │           │              │
   ▼     ▼         ▼          ▼           ▼              ▼
 §9.3  §9.2     §9.4 OCR   §9.4 OCR   §9.5 Vision    §9.6 Direct
```

| Format | Parser | Library | Τυπικό confidence |
|--------|--------|---------|-------------------|
| XML (myDATA) | XML Parser | `lxml` | 99-100% |
| PDF δομημένο | Tabular Extractor | `pdfplumber` / `camelot` | 90-98% |
| PDF scanned | OCR | `Tesseract` / Google Vision | 70-92% |
| Εικόνα | OCR | `Tesseract` / Google Vision | 70-90% |
| Catalog PDF | Vision-to-markdown | Vision LLM | 80-95% |
| Excel/CSV | Direct | `openpyxl` / `pandas` | 95-100% |

### 9.2 PDF Parsing (Structured)

Για PDF με επιλέξιμο κείμενο και πίνακες (π.χ. τυπικά τιμολόγια).

```
Strategy:
  1. pdfplumber: εξαγωγή text + table detection (lattice/stream)
  2. Αν αποτύχει η ανίχνευση πίνακα → camelot (lattice mode)
  3. Column mapping μέσω field_mapping rules (§8.2.2)
  4. Row-by-row → InvoiceItem
Fallback:
  - Αν δεν βρεθεί επιλέξιμο κείμενο → θεωρείται scanned → §9.4
Confidence:
  - Based on: % γραμμών με valid supplier_code + price
  - < 90% → ReviewQueueItem (low_confidence)
```

### 9.3 XML Parsing (myDATA)

Η **προτιμώμενη** πηγή (highest precedence, §1.4). Ελληνικά e-invoices (myDATA format).

```
Strategy:
  1. lxml parse + XSD validation (αν υπάρχει schema)
  2. XPath extraction:
     - invoiceHeader → invoice_number, invoice_date, supplier VAT
     - invoiceDetails (lines) → code, description, quantity, price, VAT
  3. Direct field mapping (deterministic, no OCR)
Confidence: 99-100% (structured data)
Σημείωση: Poimenidis → XML πάντα προτεραιότητα έναντι PDF/εικόνων
```
Παράδειγμα XPath:
```python
ns = {"icls": "http://www.aade.gr/myDATA/invoice/v1.0"}
for line in tree.xpath("//icls:invoiceDetails", namespaces=ns):
    code  = line.findtext("icls:itemCode", namespaces=ns)
    descr = line.findtext("icls:itemDescr", namespaces=ns)
    qty   = line.findtext("icls:quantity", namespaces=ns)
    price = line.findtext("icls:netValue", namespaces=ns)
```

### 9.4 Image Parsing (OCR)

Για scanned PDFs και εικόνες (JPG/PNG) — π.χ. φωτογραφίες προδιαγραφών (όπως τα Dell screenshots στο `docs/assets/`).

```
OCR Pipeline:
  1. Pre-processing: deskew, denoise, binarization, DPI normalize (300dpi)
  2. OCR engine:
     - Primary: Tesseract (lang: ell+eng — Ελληνικά + Αγγλικά)
     - High-accuracy fallback: Google Cloud Vision API
  3. Layout analysis: ανίχνευση key-value blocks / tables
  4. Post-processing: regex cleanup, number normalization
Confidence:
  - Per-word OCR confidence aggregation
  - < 90% → ReviewQueueItem (RULE R1)
```

### 9.5 Catalog PDF Parsing (Vision-to-markdown)

Για πλούσιους καταλόγους προϊόντων με εικόνες, layout, specs.

```
Vision-to-markdown approach:
  1. Render PDF pages → images (1 ανά σελίδα)
  2. Vision LLM: image → structured markdown
     (περιγραφές, specs tables, manufacturer codes, εικόνες)
  3. Parse markdown → ProductSpecification key-value pairs
  4. Image extraction → image_url (product photos)
Use case:
  - Enrichment source (precedence: Catalog, μετά το XML)
  - Manufacturer code discovery
Confidence: 80-95% (LLM-based, validated με spec key patterns)
```

### 9.6 Excel List Parsing

Για λίστες προμηθευτών σε Excel/CSV (π.χ. `από CSV σε Excel`, `ΚΑΤΗΓΟΡΙΟΠΟΙΗΣΗ`).

```
Strategy:
  1. pandas/openpyxl: read sheet(s)
  2. Header detection (πρώτη γραμμή με γνωστά labels)
  3. field_mapping rules (§8.2.2) → column → EDM field
  4. Row → InvoiceItem / Product
  5. Type coercion (numbers, dates, currencies)
Confidence: 95-100% (structured)
Edge cases: merged cells, multi-sheet → flag για review
```

### 9.7 Confidence Scoring & Fallback (γενικά)

```
CONFIDENCE FORMULA (ανά invoice):
  parsing_confidence = weighted_avg(
      field_completeness,    # % υποχρεωτικών πεδίων που βρέθηκαν
      extraction_quality,    # OCR/parser per-field confidence
      validation_pass_rate   # % γραμμών που πέρασαν validation (§8.2.3)
  )

FALLBACK CHAIN:
  XML            → (αν λείπει/invalid) → PDF structured
  PDF structured → (αν no text)        → OCR (§9.4)
  OCR            → (αν < 90%)           → ReviewQueueItem (manual)
  Catalog vision → (αν parse fail)      → manual enrichment

ROUTING DECISION:
  - supplier.parsing_profile υπερισχύει του auto-detect όταν οριστεί
  - π.χ. Poimenidis profile="xml" → προτίμηση XML ακόμη κι αν υπάρχει PDF
```


---

## 10. UI/UX Specification

Το frontend υλοποιείται με **Next.js** (React). Όλο το user-facing UI είναι στα **Ελληνικά**. Σχεδιαστική φιλοσοφία: λειτουργικότητα-πρώτα, γρήγορο review workflow, ελάχιστα clicks.

### 10.1 Screen Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    EDM UI — NAVIGATION MAP                       │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────┐
  │  Πίνακας     │  Dashboard (αρχική)
  │  Ελέγχου     │
  └──────┬───────┘
         │
  ┌──────┴───────────────────────────────────────────────┐
  │                                                        │
  ▼            ▼            ▼            ▼            ▼     ▼
┌──────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────┐ ┌────────┐
│Προμη-│  │ Ανέβασμα │  │ Προϊόντα │  │ Ουρά   │  │Export│ │Ρυθμί-  │
│θευτές│  │Τιμολογίων│  │          │  │Ελέγχου │  │      │ │σεις    │
└──────┘  └──────────┘  └────┬─────┘  └────────┘  └──────┘ └────────┘
                              │
                         ┌────▼──────┐
                         │ Λεπτομέρ. │  Product Detail/Edit
                         │ Προϊόντος │
                         └───────────┘
```

| Οθόνη | Route | Σκοπός |
|-------|-------|--------|
| Πίνακας Ελέγχου | `/` | Στατιστικά, πρόσφατα τιμολόγια, ουρά ελέγχου |
| Διαχείριση Προμηθευτών | `/suppliers` | CRUD προμηθευτών, rules, συμφωνητικά |
| Ανέβασμα Τιμολογίων | `/upload` | Drag-drop multi-file upload |
| Προϊόντα | `/products` | Search/filter/list |
| Λεπτομέρειες Προϊόντος | `/products/{id}` | View/edit, specs, ιστορικό τιμών |
| Ουρά Ελέγχου | `/review` | Review queue interface |
| Export | `/export` | Export wizard με φίλτρα |
| Ρυθμίσεις | `/settings` | Κατηγορίες, χρήστες, system config |

### 10.2 Upload Flow

```
┌─────────────────────────────────────────────────────────────┐
│  ΑΝΕΒΑΣΜΑ ΤΙΜΟΛΟΓΙΩΝ                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Προμηθευτής:  [ Ποιμενίδης Α.Ε.        ▼ ]                  │
│  Τύπος:        ( ) Τιμολόγιο  ( ) Προσφορά  ( ) Κατάλογος    │
│                                                              │
│  ┌────────────────────────────────────────────────┐         │
│  │                                                  │         │
│  │     📁  Σύρετε αρχεία εδώ ή κάντε κλικ          │         │
│  │         (PDF, XML, JPG, PNG, XLSX)               │         │
│  │                                                  │         │
│  └────────────────────────────────────────────────┘         │
│                                                              │
│  Ουρά:                                                       │
│   ✓ τιμολογιο_001.xml      [parsed]      99%   👁           │
│   ⏳ τιμολογιο_002.pdf      [parsing...]  --    --           │
│   ⚠ φωτο_003.jpg           [review]      78%   👁           │
│                                                              │
│              [ Ανέβασμα Όλων ]   [ Καθαρισμός ]              │
└─────────────────────────────────────────────────────────────┘
```

**Χαρακτηριστικά:**
- Drag-and-drop, multi-file batch upload
- Real-time status ανά αρχείο (uploaded → parsing → parsed/review)
- Inline confidence score & preview (👁)
- Dry-run rule preview πριν το final processing (§8.4)

### 10.3 Product Management

```
┌─────────────────────────────────────────────────────────────┐
│  ΛΕΠΤΟΜΕΡΕΙΕΣ ΠΡΟΪΟΝΤΟΣ — ERG-00012345                       │
├─────────────────────────────────────────────────────────────┤
│  Κωδικός Εργαλύων:    ERG-00012345     (auto, immutable)     │
│  Κωδικός Προμηθευτή:  12345            [υποχρεωτικό]         │
│  Κωδικός Κατασκευαστή:2607336  ⚠ flag  [επεξεργασία]        │
│  EAN/Barcode:         5901234123457                          │
│                                                              │
│  Περιγραφή:  ΣΕΓΑ ΣΠΑΘΟΥ BOSCH 800W                          │
│  Κατηγορία:  Εργαλεία Χειρός › Πριόνια › Σπαθόσεγες  (92%)   │
│                                                              │
│  ┌─ Προδιαγραφές ──────────────┐  ┌─ Ιστορικό Τιμών ──────┐ │
│  │ Ισχύς:    800W    [xml]      │  │  89.90€  (07/06/2026) │ │
│  │ Βάρος:    2.5kg   [catalog]  │  │  85.00€  (01/05/2026) │ │
│  │ Τάση:     220V    [manual]   │  │  📈 γράφημα           │ │
│  └─────────────────────────────┘  └───────────────────────┘ │
│                                                              │
│  Πηγή ανά πεδίο: 🟢 XML  🔵 Catalog  ⚪ Manual  🟡 Scraping  │
│                                                              │
│            [ Αποθήκευση ]   [ Εμπλουτισμός 🔄 ]              │
└─────────────────────────────────────────────────────────────┘
```

- Color-coded source badges ανά πεδίο (precedence visibility, §1.4)
- Manual edit → override όλων (source=manual)
- Κουμπί "Εμπλουτισμός" → trigger `POST /products/{id}/enrich`

### 10.4 Review Queue Interface

```
┌─────────────────────────────────────────────────────────────┐
│  ΟΥΡΑ ΕΛΕΓΧΟΥ                            42 ανοιχτά items     │
├─────────────────────────────────────────────────────────────┤
│  Φίλτρα: [Όλα ▼] [Προτεραιότητα: HIGH ▼] [Τύπος: Όλα ▼]      │
│                                                              │
│  🔴 CRITICAL  Πιθανό διπλότυπο — ERG-00012345 vs ERG-00012999│
│  🟠 HIGH      Λείπει κωδικός κατασκευαστή — "12345"          │
│      ┌──────────────────────────────────────────────────┐   │
│      │ Θα χρησιμοποιηθεί ο κωδικός προμηθευτή ως          │   │
│      │ κωδικός κατασκευαστή;                              │   │
│      │   [ Ναι ]  [ Όχι ]  [ Εισαγωγή χειροκίνητα ]      │   │
│      └──────────────────────────────────────────────────┘   │
│  🟡 MEDIUM    Ανωμαλία τιμής +62% — ERG-00013100             │
│                                                              │
│  Μαζικές ενέργειες: [ Έγκριση ]  [ Απόρριψη ]  [ Παράβλεψη ] │
└─────────────────────────────────────────────────────────────┘
```

- Sorted by priority (CRITICAL πρώτα, §7.4)
- Inline resolution (Approve/Edit/Reject) χωρίς αλλαγή σελίδας
- Το ειδικό prompt manufacturer code εμφανίζεται με τα 3 options (§7.3.1)
- Batch actions για όμοια items

### 10.5 Search & Filtering

```
┌─────────────────────────────────────────────────────────────┐
│  ΠΡΟΪΟΝΤΑ                                    [+ Νέο Προϊόν]   │
├─────────────────────────────────────────────────────────────┤
│  🔍 [ Αναζήτηση: κωδικός / περιγραφή / EAN          ]        │
│  Φίλτρα: [Προμηθευτής ▼] [Κατηγορία K1/K2/K3 ▼] [Πληρότητα ▼]│
├─────────────────────────────────────────────────────────────┤
│  Κωδ.Εργαλ. │ Περιγραφή         │ Κατηγορία  │ Τιμή  │Πληρότ.│
│  ERG-..2345 │ ΣΕΓΑ ΣΠΑΘΟΥ 800W  │ Σπαθόσεγες │89.90€ │ 95% │
│  ERG-..2400 │ ΔΡΑΠΑΝΟ 18V       │ Δράπανα    │129.0€ │ 80% │
│  ...                                              [1][2][3]→ │
└─────────────────────────────────────────────────────────────┘
```

- Full-text search (trigram, §5.3) σε description / κωδικούς / EAN
- Multi-level category filter (K1 → K2 → K3 cascading)
- Φίλτρο `data_completeness_score` (εντοπισμός ελλιπών προϊόντων)
- Server-side pagination (`limit`/`offset`)

### 10.6 Dashboard (Πίνακας Ελέγχου)

```
┌─────────────────────────────────────────────────────────────┐
│  ΠΙΝΑΚΑΣ ΕΛΕΓΧΟΥ                                              │
├─────────────────────────────────────────────────────────────┤
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                │
│  │ 1,240  │ │   28   │ │   42   │ │  98%   │                │
│  │Προϊόντα│ │Τιμολόγ.│ │ Review │ │Επιτυχία│                │
│  │        │ │ σήμερα │ │ ανοιχτά│ │ parsing│                │
│  └────────┘ └────────┘ └────────┘ └────────┘                │
│                                                              │
│  Πρόσφατα Τιμολόγια            │  Ουρά Ελέγχου (top 5)        │
│   ✓ Ποιμενίδης  τιμ_001  99%   │  🔴 Διπλότυπο ERG-..345     │
│   ⏳ Ποιμενίδης τιμ_002  --    │  🟠 Κωδ.κατασκ. "12345"     │
│   ⚠ Άλλος       φωτο_003 78%   │  🟡 Τιμή +62% ERG-..100     │
└─────────────────────────────────────────────────────────────┘
```

**Workflow diagram (τυπική χρήση):**
```
Upload → (auto parse+normalize) → Review ανοιχτών items → Approve/Edit
   → Products ενημερωμένα → Export → χρήση σε εξωτερικά συστήματα
```


---

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
