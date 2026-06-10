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
