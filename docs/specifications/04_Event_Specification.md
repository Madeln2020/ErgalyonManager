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
