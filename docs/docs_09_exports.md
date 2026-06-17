# 09 — Exports

## 9.1 Τι είναι export
Export = παραγωγή δομημένου αρχείου από το EDM που μπορεί να χρησιμοποιηθεί downstream.

> Το ακριβές format/στήλες κλειδώνει σε ξεχωριστό “Export Contract” όταν συμφωνηθεί.

## 9.2 Export contracts (versioned)
Πρόταση: κάθε export type έχει:
- `export_type`
- `version`
- schema definition
- validation rules

## 9.3 Common validations
- required fields present
- decimals normalized
- SKU exists
- no negative qty
- totals consistent

## 9.4 Preview
- πριν το download, ο χρήστης βλέπει preview table
- warnings / errors

## 9.5 Storage & reproducibility
- store export artifact in MinIO
- store metadata:
  - which document ids
  - when
  - by whom
  - contract version

## 9.6 Rollback
- export δεν αλλάζει δεδομένα
- αν downstream θέλει re-run, μπορεί να γίνει deterministic re-export
