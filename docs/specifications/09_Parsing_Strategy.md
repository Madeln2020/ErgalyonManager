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
