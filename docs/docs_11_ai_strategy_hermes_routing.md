# 11 — AI Strategy & Hermes Routing

## 11.1 Τι κάνει το AI στο EDM v2
AI χρησιμοποιείται για:
- extraction fallback (όταν deterministic αποτυγχάνει)
- candidate suggestions για matching
- semantic search (RAG) σε supplier documents

AI ΔΕΝ χρησιμοποιείται ως:
- αυτόματος judge για compliance
- source of truth χωρίς review

## 11.2 Hermes: responsibilities
Hermes είναι ο router/orchestrator:
- παίρνει task request
- εφαρμόζει policy
- καλεί το κατάλληλο model/provider
- επιστρέφει structured output
- γράφει metrics/logs

## 11.3 Providers
- **Local**: local LLM runtime (CPU/GPU) για privacy/latency
- **freeLLMAPI**: external provider (fallback)
- **Abacus API**: external provider (fallback ή high-accuracy)

## 11.4 Routing policy (examples)
### Privacy-first
- Αν payload περιέχει VAT numbers / tax ids → local only.

### Reliability
- Αν local fails 2 φορές → fallback to external (freeLLMAPI → Abacus).

### Task-based
- `ocr_cleanup` → local small model
- `invoice_table_to_json` → prefer local; fallback external
- `rag_search` → local embeddings

## 11.5 Output contracts
Κάθε AI call πρέπει να έχει:
- `schema_version`
- `result_json`
- `confidence`
- `warnings`
- `model_used`
- `tokens/cost` (αν διαθέσιμο)

## 11.6 Evaluation harness (recommended)
- nightly run σε fixed corpus
- metrics:
  - extraction accuracy
  - match suggestion top-1/top-3
  - time per doc

## 11.7 Guardrails
- max tokens
- regex validation των numeric fields
- strict JSON parsing

## 11.8 Human review integration
- AI suggestions never auto-apply when low confidence
- always show “why” panel
