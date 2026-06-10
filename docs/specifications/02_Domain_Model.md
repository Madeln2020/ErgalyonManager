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
