# 12 — Security, Privacy, Audit

## 12.1 Data classification
- Supplier VAT numbers (ΑΦΜ) = sensitive.
- Invoices may contain personal data (names, phones).

## 12.2 Storage
- MinIO bucket policies
- encryption at rest (όπου δυνατό)
- TLS in transit

## 12.3 Access control
- RBAC:
  - admin
  - operator
  - viewer

## 12.4 Audit logs
Audit πρέπει να καλύπτει:
- uploads
- rule changes
- match decisions
- enrichment edits
- exports

Fields:
- who
- when
- what changed
- entity reference

## 12.5 Secrets management
- secrets μόνο σε env/secret store
- ποτέ στο git

## 12.6 External AI policy
- Hermes enforce policy: payload redaction όπου χρειάζεται
- blocklist fields that never leave

## 12.7 Backups
- DB backups + restore drill
- MinIO object replication/snapshots

## 12.8 Incident handling
- revoke keys
- rotate secrets
- disable external routing if needed
