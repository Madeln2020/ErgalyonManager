// Common types shared across frontend pages

export interface Product {
  id: string
  canonical_name: string
  internal_code: string | null
  status: 'active' | 'provisional' | 'archived'
  technical_specs_json: { [key: string]: any } | null
  category_path: string | null
  created_at: string
  updated_at: string
}

export interface Supplier {
  id: string
  name: string
  vat_number: string | null
  default_currency: string
  rules_json: { [key: string]: any } | null
  is_active: boolean
  created_at: string
}

export interface MatchDecision {
  id: string
  parsed_line_item_id: string
  product_id: string | null
  product_supplier_link_id: string | null
  decision_type: 'auto_exact' | 'auto_suggested' | 'manual_confirm' | 'manual_override'
  candidates_json: { [key: string]: any } | null
  decided_at: string | null
}

export interface EnrichmentEvent {
  id: string
  product_id: string
  source_type: string
  source_ref: string | null
  changes_json: { [key: string]: any } | null
  applied_at: string | null
  created_at: string
}

export interface EnrichmentQueueItem {
  id: string
  product_id: string
  source: string | null
  enrichment_level: string | null
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  created_at: string
  started_at: string | null
  completed_at: string | null
  error_message: string | null
}

export interface ReviewTask {
  id: string
  task_type: string
  entity_ref: string | null
  status: 'open' | 'in_progress' | 'done'
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  assigned_to: string | null
  created_at: string
}
