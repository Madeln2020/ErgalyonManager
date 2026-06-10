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
