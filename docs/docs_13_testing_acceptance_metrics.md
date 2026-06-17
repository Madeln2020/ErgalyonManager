# 13 — Testing, Acceptance, Metrics

## 13.1 Test layers
- Unit tests: normalization functions, parsing helpers
- Integration tests: parse pipeline against fixtures
- E2E tests: upload → parse → review decisions → export

## 13.2 Golden corpus
- Αρχεία Poimenidis (ανωνυμοποιημένα όπου χρειάζεται)
- annotated expected outputs:
  - extracted line items
  - normalized SKUs
  - matching outcomes

## 13.3 Acceptance criteria (MVP)
- Parse success rate >= 90% σε Poimenidis corpus
- Normalization correctness >= 95%
- Review time per document μειώνεται με iterations
- Export validation passes 100% για approved docs

## 13.4 Metrics to track
- documents/day
- average time to approve
- % auto_exact matches
- % manual overrides
- enrichment coverage (% products with required specs)

## 13.5 Regression policy
- κάθε αλλαγή στους rules ή parser version τρέχει test suite
- store parser_version in outputs
