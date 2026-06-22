// frontend/src/app/matching/page.tsx
'use client'

import { useEffect, useState, useCallback } from 'react'
import { apiFetch } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'

// ─── Interfaces ────────────────────────────────────────────────────────────────
interface Candidate {
  product_id: string
  name: string
  score: number
  match_reason: string
}

interface MatchDecision {
  id: string
  parsed_line_item_id: string
  product_id: string | null
  product_supplier_link_id: string | null
  decision_type: 'auto_exact' | 'auto_suggested' | 'manual_confirm' | 'manual_override'
  candidates_json: Candidate[]
  decided_at: string | null
  created_at?: string
  parsed_document_id?: string
  parsed_document_name?: string
  supplier_sku?: string
  description_raw?: string
  line_index?: number
}

interface Product {
  id: string
  canonical_name: string
}

interface NewProductForm {
  name: string
  description: string
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const typeColors: Record<string, string> = {
  auto_exact: 'bg-green-100 text-green-800 border-green-300',
  auto_suggested: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  manual_confirm: 'bg-blue-100 text-blue-800 border-blue-300',
  manual_override: 'bg-purple-100 text-purple-800 border-purple-300',
}

const typeLabels: Record<string, string> = {
  auto_exact: 'Auto Exact',
  auto_suggested: 'Auto Suggested',
  manual_confirm: 'Manual Confirm',
  manual_override: 'Manual Override',
}

// ─── Confirm Modal Component ───────────────────────────────────────────────────
function ConfirmModal({
  title,
  message,
  confirmLabel,
  confirmColor,
  onConfirm,
  onCancel,
}: {
  title: string
  message: string
  confirmLabel: string
  confirmColor: string
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
          >
            Άκυρο
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors ${confirmColor}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Create Product Modal ─────────────────────────────────────────────────────
function CreateProductModal({
  onCreated,
  onCancel,
}: {
  onCreated: (product: { id: string; name: string }) => void
  onCancel: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)
  const { token } = useAuth()

  const handleCreate = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      const res = await apiFetch<{ id: string; name: string }>('/api/v1/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ canonical_name: name, description: description || name }),
      })
      onCreated(res)
    } catch (e) {
      console.error('Failed to create product', e)
      alert('Σφάλμα δημιουργίας προϊόντος')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Δημιουργία Νέου Προϊόντος</h3>
        <div className="space-y-3 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Όνομα *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="π.χ. ΔΡΑΠΑΝΟ 18V MAKITA"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Περιγραφή</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Προαιρετική περιγραφή..."
            />
          </div>
        </div>
        <div className="flex gap-3 justify-end">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200">
            Άκυρο
          </button>
          <button
            onClick={handleCreate}
            disabled={!name.trim() || saving}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Δημιουργία...' : 'Δημιούργησε'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Score Badge ───────────────────────────────────────────────────────────────
function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color =
    pct >= 90 ? 'bg-green-100 text-green-800' :
    pct >= 70 ? 'bg-yellow-100 text-yellow-800' :
    'bg-red-100 text-red-800'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${color}`}>
      {pct}%
    </span>
  )
}

// ─── Main Component ────────────────────────────────────────────────────────────
export default function MatchingPage() {
  const { token } = useAuth()
  const router = useRouter()

  const [decisions, setDecisions] = useState<MatchDecision[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedType, setSelectedType] = useState<string>('all')

  // Bulk selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  // Guardrail modals
  const [confirmModal, setConfirmModal] = useState<{
    title: string; message: string; confirmLabel: string; confirmColor: string
    onConfirm: () => void
  } | null>(null)

  // Create product modal
  const [createProductTarget, setCreateProductTarget] = useState<{
    decisionId: string; parsedLineItemId: string; name: string
  } | null>(null)
  const [newProductName, setNewProductName] = useState('')

  // Expanded candidate rows
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  // Provenance tooltip
  const [provenanceTooltip, setProvenanceTooltip] = useState<{
    decision: MatchDecision
    x: number; y: number
  } | null>(null)

  const fetchData = useCallback(() => {
    if (!token) return
    setLoading(true)
    Promise.all([
      apiFetch('/api/v1/matching'),
      apiFetch('/api/v1/products?limit=10000'),
    ])
      .then(([decisionsData, productsData]: [any, any]) => {
        setDecisions(Array.isArray(decisionsData) ? decisionsData : [])
        setProducts(Array.isArray(productsData) ? productsData : [])
        setLoading(false)
      })
      .catch((err: unknown) => {
        console.error('Failed to fetch matching data:', err)
        setLoading(false)
      })
  }, [token])

  useEffect(() => { fetchData() }, [fetchData])

  const filteredDecisions = selectedType === 'all'
    ? decisions
    : decisions.filter((d) => d.decision_type === selectedType)

  const stats = {
    total: decisions.length,
    autoExact: decisions.filter((d) => d.decision_type === 'auto_exact').length,
    autoSuggested: decisions.filter((d) => d.decision_type === 'auto_suggested').length,
    manual: decisions.filter((d) => d.decision_type === 'manual_confirm' || d.decision_type === 'manual_override').length,
  }

  // ── Bulk Actions ──────────────────────────────────────────────────────────
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const selectAll = () => {
    if (selectedType === 'all') {
      setSelectedIds(new Set(filteredDecisions.map((d) => d.id)))
    } else {
      const suggested = filteredDecisions.filter((d) => d.decision_type === 'auto_suggested').map((d) => d.id)
      setSelectedIds(new Set(suggested))
    }
  }

  const clearSelection = () => setSelectedIds(new Set())

  const bulkApproveSuggested = () => {
    const toApprove = filteredDecisions.filter(
      (d) => selectedIds.has(d.id) && d.decision_type === 'auto_suggested' && d.candidates_json?.length > 0
    )
    if (toApprove.length === 0) return
    setConfirmModal({
      title: `Έγκριση ${toApprove.length} προτάσεων`,
      message: `Θα επιβεβαιωθούν ${toApprove.length} αυτόματες προτάσεις αντιστοίχισης. Συνέχεια;`,
      confirmLabel: `Έγκριση ${toApprove.length}`,
      confirmColor: 'bg-blue-600 hover:bg-blue-700',
      onConfirm: async () => {
        setConfirmModal(null)
        await Promise.all(
          toApprove.map((d) =>
            apiFetch('/api/v1/matching', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                parsed_line_item_id: d.parsed_line_item_id,
                product_id: d.candidates_json[0].product_id,
                decision_type: 'manual_confirm',
              }),
            })
          )
        )
        setSelectedIds(new Set())
        fetchData()
      },
    })
  }

  const bulkReject = () => {
    const toReject = filteredDecisions.filter(
      (d) => selectedIds.has(d.id) && d.decision_type === 'auto_suggested'
    )
    if (toReject.length === 0) return
    setConfirmModal({
      title: `Απόρριψη ${toReject.length} προτάσεων`,
      message: `Θα απορριφθούν ${toReject.length} αυτόματες προτάσεις. Τα αντίστοιχα προϊόντα θα μείνουν ως έχουν χωρίς αντιστοίχιση.`,
      confirmLabel: `Απόρριψη ${toReject.length}`,
      confirmColor: 'bg-red-600 hover:bg-red-700',
      onConfirm: async () => {
        setConfirmModal(null)
        await Promise.all(
          toReject.map((d) =>
            apiFetch(`/api/v1/matching/${d.id}`, {
              method: 'DELETE',
            }).catch(console.error)
          )
        )
        setSelectedIds(new Set())
        fetchData()
      },
    })
  }

  // ── Single Row Actions ────────────────────────────────────────────────────
  const handleConfirmCandidate = async (decision: MatchDecision, candidate: Candidate) => {
    setConfirmModal({
      title: 'Επιβεβαίωση Αντιστοίχισης',
      message: `Αντιστοίχιση με "${candidate.name}" (ομοιότητα ${Math.round(candidate.score * 100)}%);`,
      confirmLabel: 'Επιβεβαίωση',
      confirmColor: 'bg-green-600 hover:bg-green-700',
      onConfirm: async () => {
        setConfirmModal(null)
        await apiFetch('/api/v1/matching', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            parsed_line_item_id: decision.parsed_line_item_id,
            product_id: candidate.product_id,
            decision_type: 'manual_confirm',
          }),
        })
        fetchData()
      },
    })
  }

  const handleOverride = async (target: { parsedLineItemId: string }) => {
    if (!newProductName.trim()) return
    setConfirmModal({
      title: 'Δημιουργία & Αντιστοίχιση',
      message: `Δημιουργία νέου προϊόντος "${newProductName}" και αντιστοίχιση με αυτό.`,
      confirmLabel: 'Δημιούργησε & Αντιστοίχισε',
      confirmColor: 'bg-purple-600 hover:bg-purple-700',
      onConfirm: async () => {
        setConfirmModal(null)
        setCreateProductTarget(null)
        setNewProductName('')
        try {
          const prod = await apiFetch<{ id: string; canonical_name: string }>('/api/v1/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ canonical_name: newProductName, description: newProductName }),
          })
          await apiFetch('/api/v1/matching', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              parsed_line_item_id: target.parsedLineItemId,
              product_id: prod.id,
              decision_type: 'manual_override',
            }),
          })
          fetchData()
        } catch (e) {
          console.error('Override failed', e)
          alert('Σφάλμα κατά την αντιστοίχιση')
        }
      },
    })
  }

  const handleDelete = (decision: MatchDecision) => {
    setConfirmModal({
      title: 'Διαγραφή Αντιστοίχισης',
      message: 'Αυτή η ενέργεια θα διαγράψει την απόφαση αντιστοίχισης. Θέλετε να συνεχίσετε;',
      confirmLabel: 'Διαγραφή',
      confirmColor: 'bg-red-600 hover:bg-red-700',
      onConfirm: async () => {
        setConfirmModal(null)
        await apiFetch(`/api/v1/matching/${decision.id}`, { method: 'DELETE' }).catch(console.error)
        fetchData()
      },
    })
  }

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const getProductName = (productId: string | null) => {
    if (!productId) return '—'
    const p = products.find((p: Product) => p.id === productId)
    return p ? p.canonical_name.slice(0, 60) : productId.slice(0, 8) + '...'
  }

  const selectedSuggested = filteredDecisions.filter(
    (d) => selectedIds.has(d.id) && d.decision_type === 'auto_suggested'
  ).length

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Αντιστοίχιση Προϊόντων</h1>
          <p className="text-sm text-gray-500 mt-1">Αναθεώρηση & επιβεβαίωση αντιστοιχίσεων</p>
        </div>
        <button
          onClick={fetchData}
          className="px-4 py-2 text-sm font-medium bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          🔄 Ανανέωση
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Σύνολο', value: stats.total, color: 'from-gray-500 to-gray-600' },
          { label: 'Auto Exact', value: stats.autoExact, color: 'from-green-500 to-green-600' },
          { label: 'Auto Suggested', value: stats.autoSuggested, color: 'from-yellow-400 to-yellow-500' },
          { label: 'Χειροκίνητα', value: stats.manual, color: 'from-blue-500 to-blue-600' },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-600">{stat.label}</span>
              <div className={`w-3 h-3 rounded-full bg-gradient-to-r ${stat.color}`} />
            </div>
            <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Filter + Bulk Actions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Filters */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-gray-700">Φίλτρο:</span>
            {['all', 'auto_exact', 'auto_suggested', 'manual_confirm', 'manual_override'].map((type) => (
              <button
                key={type}
                onClick={() => { setSelectedType(type); clearSelection() }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  selectedType === type
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {type === 'all' ? 'Όλα' : typeLabels[type]}
              </button>
            ))}
          </div>

          {/* Bulk Actions */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">
              {selectedIds.size > 0 ? `${selectedIds.size} επιλεγμένα` : ''}
            </span>
            <button
              onClick={selectAll}
              className="px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              Επιλογή όλων
            </button>
            {selectedIds.size > 0 && (
              <>
                <button
                  onClick={clearSelection}
                  className="px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  Καθαρισμός
                </button>
                {selectedSuggested > 0 && (
                  <>
                    <button
                      onClick={bulkApproveSuggested}
                      className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      ✅ Επιβεβαίωση {selectedSuggested}
                    </button>
                    <button
                      onClick={bulkReject}
                      className="px-3 py-1.5 text-xs font-medium bg-red-600 text-white rounded-lg hover:bg-red-700"
                    >
                      ❌ Απόρριψη {selectedSuggested}
                    </button>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Decisions Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Αποφάσεις Αντιστοίχισης</h2>
          <span className="text-xs text-gray-500">{filteredDecisions.length} εγγραφές</span>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <p className="mt-3 text-sm text-gray-500">Φόρτωση...</p>
          </div>
        ) : filteredDecisions.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            <p className="text-4xl mb-2">📭</p>
            <p>Δεν βρέθηκαν αποφάσεις αντιστοίχισης</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="w-10 px-4 py-3">
                    <span className="sr-only">Επιλογή</span>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Τύπος</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Προϊόν</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU / Περιγραφή</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Candidates</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Προέλευση</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ενέργειες</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredDecisions.map((decision: MatchDecision, idx: number) => {
                  const isExpanded = expandedIds.has(decision.id)
                  const hasCandidates = decision.candidates_json?.length > 0

                  return (
                    <tr
                      key={decision.id}
                      className={`hover:bg-gray-50 ${selectedIds.has(decision.id) ? 'bg-blue-50' : ''}`}
                    >
                      {/* Checkbox */}
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(decision.id)}
                          onChange={() => toggleSelect(decision.id)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                      </td>

                      {/* # */}
                      <td className="px-4 py-3 text-xs text-gray-400">{idx + 1}</td>

                      {/* Type Badge */}
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${typeColors[decision.decision_type]}`}>
                          {typeLabels[decision.decision_type]}
                        </span>
                      </td>

                      {/* Product */}
                      <td className="px-4 py-3 text-sm text-gray-900 max-w-[200px]">
                        <div className="flex items-center gap-1">
                          <span className="truncate">{getProductName(decision.product_id)}</span>
                          {decision.product_id && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                router.push(`/products/${decision.product_id}`)
                              }}
                              className="text-blue-500 hover:text-blue-700 text-xs"
                              title="Προβολή προϊόντος"
                            >
                              👁
                            </button>
                          )}
                        </div>
                      </td>

                      {/* SKU / Description */}
                      <td className="px-4 py-3 text-xs text-gray-500 max-w-[200px]">
                        {decision.supplier_sku && (
                          <div className="font-mono text-gray-700">{decision.supplier_sku}</div>
                        )}
                        {decision.description_raw && (
                          <div className="truncate text-gray-400">{decision.description_raw}</div>
                        )}
                      </td>

                      {/* Candidates */}
                      <td className="px-4 py-3">
                        {hasCandidates ? (
                          <div>
                            <button
                              onClick={() => toggleExpand(decision.id)}
                              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                            >
                              {isExpanded ? '▲ Κλείσιμο' : `▼ ${decision.candidates_json.length} υποψήφιοι`}
                            </button>
                            {isExpanded && (
                              <div className="mt-2 space-y-1 max-w-xs">
                                {decision.candidates_json.map((c, ci) => (
                                  <div key={ci} className="bg-gray-50 rounded-lg p-2 text-xs">
                                    <div className="flex items-center justify-between">
                                      <span className="font-medium text-gray-800 truncate max-w-[160px]">{c.name}</span>
                                      <ScoreBadge score={c.score} />
                                    </div>
                                    {c.match_reason && (
                                      <p className="text-gray-400 mt-0.5">{c.match_reason}</p>
                                    )}
                                    {decision.decision_type === 'auto_suggested' && (
                                      <div className="flex gap-1 mt-1">
                                        <button
                                          onClick={() => handleConfirmCandidate(decision, c)}
                                          className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
                                        >
                                          ✅ Επιλογή
                                        </button>
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>

                      {/* Provenance */}
                      <td className="px-4 py-3">
                        <button
                          className="text-xs text-gray-400 hover:text-gray-700"
                          onClick={(e) =>
                            setProvenanceTooltip({
                              decision,
                              x: e.clientX,
                              y: e.clientY,
                            })
                          }
                          title="Προβολή προέλευσης"
                        >
                          ℹ️
                        </button>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {/* Create new + override */}
                          {decision.decision_type === 'auto_suggested' && (
                            <button
                              onClick={() => {
                                setCreateProductTarget({
                                  decisionId: decision.id,
                                  parsedLineItemId: decision.parsed_line_item_id,
                                  name: decision.description_raw || decision.supplier_sku || '',
                                })
                                setNewProductName(decision.description_raw || decision.supplier_sku || '')
                              }}
                              className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                              title="Δημιουργία νέου προϊόντος"
                            >
                              +Νέο
                            </button>
                          )}
                          {/* Delete */}
                          <button
                            onClick={() => handleDelete(decision)}
                            className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                            title="Διαγραφή"
                          >
                            🗑
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Confirm Modal */}
      {confirmModal && (
        <ConfirmModal
          title={confirmModal.title}
          message={confirmModal.message}
          confirmLabel={confirmModal.confirmLabel}
          confirmColor={confirmModal.confirmColor}
          onConfirm={confirmModal.onConfirm}
          onCancel={() => setConfirmModal(null)}
        />
      )}

      {/* Create Product Modal */}
      {createProductTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Δημιουργία Νέου Προϊόντος</h3>
            <p className="text-sm text-gray-500 mb-3">
              Δημιουργία νέου κανονικοποιημένου προϊόντος και αντιστοίχιση με το line item.
            </p>
            <input
              type="text"
              value={newProductName}
              onChange={(e) => setNewProductName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
              placeholder="Όνομα προϊόντος..."
              autoFocus
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => { setCreateProductTarget(null); setNewProductName('') }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200"
              >
                Άκυρο
              </button>
              <button
                onClick={() => handleOverride({ parsedLineItemId: createProductTarget!.parsedLineItemId })}
                disabled={!newProductName.trim()}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
              >
                Δημιούργησε & Αντιστοίχισε
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Provenance Tooltip */}
      {provenanceTooltip && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setProvenanceTooltip(null)} />
          <div
            className="fixed z-50 bg-white border border-gray-200 rounded-xl shadow-xl p-4 text-sm max-w-xs"
            style={{ left: Math.min(provenanceTooltip.x + 10, window.innerWidth - 300), top: provenanceTooltip.y + 10 }}
          >
            <h4 className="font-bold text-gray-800 mb-2">📋 Προέλευση</h4>
            <div className="space-y-1 text-gray-600">
              <p><span className="font-medium text-gray-700">Τύπος:</span> {typeLabels[provenanceTooltip.decision.decision_type]}</p>
              <p><span className="font-medium text-gray-700">Δημιουργήθηκε:</span> {provenanceTooltip.decision.created_at ? new Date(provenanceTooltip.decision.created_at).toLocaleString('el-GR') : '—'}</p>
              <p><span className="font-medium text-gray-700">Αποφασίστηκε:</span> {provenanceTooltip.decision.decided_at ? new Date(provenanceTooltip.decision.decided_at).toLocaleString('el-GR') : '—'}</p>
              <p><span className="font-medium text-gray-700">Candidates:</span> {provenanceTooltip.decision.candidates_json?.length ?? 0}</p>
            </div>
            <button
              onClick={() => setProvenanceTooltip(null)}
              className="mt-3 text-xs text-gray-400 hover:text-gray-600"
            >
              Κλείσιμο
            </button>
          </div>
        </>
      )}
    </div>
  )
}