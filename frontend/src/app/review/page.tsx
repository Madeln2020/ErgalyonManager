'use client'

import { useEffect, useState, useCallback } from 'react'
import DashboardLayout from '../DashboardLayout'

interface Supplier { id: string; name: string }
interface ReviewItem {
  id: string
  product_id: string | null
  invoice_item_id: string | null
  review_type: string
  priority: string
  status: string
  resolution: string | null
  payload_json: Record<string, any> | null
  prompt_text: string | null
  created_at: string
}
interface ProductsCache { [id: string]: { ergalyon_code: string; description: string } }

const priorityColors: Record<string, string> = {
  CRITICAL: 'border-red-300 bg-red-50',
  HIGH: 'border-orange-300 bg-orange-50',
  MEDIUM: 'border-yellow-300 bg-yellow-50',
  LOW: 'border-gray-200 bg-gray-50',
}

const typeLabels: Record<string, { label: string; icon: string }> = {
  duplicate: { label: 'Πιθανό διπλότυπο', icon: '🔴' },
  missing_manufacturer_code: { label: 'Λείπει κωδικός κατασκευαστή', icon: '🟠' },
  low_confidence: { label: 'Χαμηλό confidence', icon: '🟡' },
  price_anomaly: { label: 'Ανωμαλία τιμής', icon: '📈' },
  new_supplier: { label: 'Νέος προμηθευτής', icon: '🔵' },
}

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('open')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [supplierFilter, setSupplierFilter] = useState('')
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [products, setProducts] = useState<ProductsCache>({})
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  const [resolvingIds, setResolvingIds] = useState<Set<string>>(new Set())
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const showToast = useCallback((type: 'success' | 'error', message: string) => {
    setToast({ type, message })
    setTimeout(() => setToast(null), 3000)
  }, [])

  // Fetch suppliers
  useEffect(() => {
    fetch('/api/v1/suppliers')
      .then(r => r.json())
      .then(data => setSuppliers(Array.isArray(data) ? data : []))
      .catch(() => {})
  }, [])

  // Fetch review items
  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ status: filter, limit: '50' })
    if (priorityFilter) params.set('priority', priorityFilter)
    if (typeFilter) params.set('review_type', typeFilter)

    fetch(`/api/v1/review-queue?${params.toString()}`)
      .then(r => r.json())
      .then(data => {
        const newItems = data.items || []
        setItems(newItems)
        setTotal(data.total || 0)
        setSelectedItems(new Set())
        setLoading(false)

        // Load product data for items that have product_id
        const productIds = newItems
          .filter((i: ReviewItem) => i.product_id)
          .map((i: ReviewItem) => i.product_id)
          .filter(Boolean) as string[]

        if (productIds.length > 0) {
          const seen = new Set<string>()
          const unique = productIds.filter(id => {
            if (seen.has(id)) return false
            seen.add(id); return true
          }).slice(0, 20)
          unique.forEach(async (pid) => {
            try {
              const res = await fetch(`/api/v1/products/${pid}`)
              if (res.ok) {
                const p = await res.json()
                setProducts(prev => ({ ...prev, [pid]: { ergalyon_code: p.ergalyon_code, description: p.description } }))
              }
            } catch {}
          })
        }
      })
      .catch(() => { setLoading(false); })
  }, [filter, priorityFilter, typeFilter])

  const handleResolve = async (id: string, resolution: string) => {
    setResolvingIds(prev => new Set(prev).add(id))
    try {
      const res = await fetch(`/api/v1/review-queue/${id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution, data: {} }),
      })
      if (!res.ok) throw new Error('Resolve failed')
      setItems(prev => prev.filter(i => i.id !== id))
      setTotal(prev => Math.max(0, prev - 1))
      showToast('success', resolution === 'approved' ? 'Εγκρίθηκε' : resolution === 'rejected' ? 'Απορρίφθηκε' : 'Ενημερώθηκε')
    } catch (err: any) {
      showToast('error', 'Σφάλμα: ' + err.message)
    } finally {
      setResolvingIds(prev => { const next = new Set(prev); next.delete(id); return next })
    }
  }

  const handleBulkResolve = async (resolution: string) => {
    const ids: string[] = []
    selectedItems.forEach(id => ids.push(id))
    if (ids.length === 0) return
    setResolvingIds(prev => new Set([...prev, ...ids]))
    try {
      const results = await Promise.allSettled(
        ids.map(id =>
          fetch(`/api/v1/review-queue/${id}/resolve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resolution, data: {} }),
          })
        )
      )
      const succeeded = results.filter(r => r.status === 'fulfilled').length
      const failed = results.filter(r => r.status === 'rejected').length
      if (succeeded > 0) {
        setItems(prev => prev.filter(i => !ids.includes(i.id)))
        setTotal(prev => Math.max(0, prev - succeeded))
        setSelectedItems(new Set())
        showToast('success', `${succeeded} items ${resolution === 'approved' ? 'εγκρίθηκαν' : resolution === 'rejected' ? 'απορρίφθηκαν' : 'ενημερώθηκαν'}`)
      }
      if (failed > 0) showToast('error', `${failed} items απέτυχαν`)
    } catch (err: any) {
      showToast('error', 'Σφάλμα μαζικής ενέργειας: ' + err.message)
    } finally {
      setResolvingIds(new Set())
    }
  }

  const toggleSelect = (id: string) => {
    setSelectedItems(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  return (
    <DashboardLayout>
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all ${
          toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {toast.message}
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Ουρά Ελέγχου</h2>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-500">{total} ανοιχτά</span>
          {selectedItems.size > 0 && (
            <span className="text-blue-600 font-medium">{selectedItems.size} επιλεγμένα</span>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        {/* Status tabs */}
        <div className="flex gap-1">
          {[
            { key: 'open', label: 'Ανοιχτά' },
            { key: 'in_progress', label: 'Σε εξέλιξη' },
            { key: 'resolved', label: 'Ολοκληρωμένα' },
          ].map(s => (
            <button
              key={s.key}
              onClick={() => setFilter(s.key)}
              className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                filter === s.key
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
              }`}
            >{s.label}</button>
          ))}
        </div>

        {/* Priority filter */}
        <select
          value={priorityFilter}
          onChange={e => setPriorityFilter(e.target.value)}
          className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Όλες οι προτεραιότητες</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>

        {/* Review type filter */}
        <select
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
          className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Όλοι οι τύποι</option>
          {Object.entries(typeLabels).map(([k, v]) => (
            <option key={k} value={k}>{v.icon} {v.label}</option>
          ))}
        </select>
      </div>

      {/* Bulk actions */}
      {selectedItems.size > 0 && filter !== 'resolved' && (
        <div className="flex items-center gap-2 mb-4 px-3 py-2 bg-blue-50 border border-blue-100 rounded-lg">
          <span className="text-xs text-blue-700 font-medium">{selectedItems.size} επιλεγμένα:</span>
          <button onClick={() => handleBulkResolve('approved')} className="px-3 py-1 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
            ✓ Έγκριση Όλων
          </button>
          <button onClick={() => handleBulkResolve('rejected')} className="px-3 py-1 text-xs bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors">
            ✕ Απόρριψη Όλων
          </button>
          <button onClick={() => setSelectedItems(new Set())} className="px-3 py-1 text-xs text-gray-500 hover:text-gray-700">
            Ακύρωση
          </button>
        </div>
      )}

      {/* List */}
      <div className="space-y-2">
        {loading ? (
          <div className="text-center py-12 text-gray-400">Φόρτωση...</div>
        ) : items.length === 0 ? (
          <div className="text-center py-12 text-gray-400">Δεν υπάρχουν items σε αυτή την κατηγορία</div>
        ) : items.map((item) => {
          const typeInfo = typeLabels[item.review_type] || { label: item.review_type, icon: '🔵' }
          const product = item.product_id ? products[item.product_id] : null
          const isSelected = selectedItems.has(item.id)
          const isResolving = resolvingIds.has(item.id)

          return (
            <div
              key={item.id}
              className={`bg-white rounded-xl border p-4 transition-all ${
                priorityColors[item.priority] || 'border-gray-100'
              } ${isSelected ? 'ring-2 ring-blue-400' : ''}`}
            >
              <div className="flex items-start gap-3">
                {/* Checkbox */}
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleSelect(item.id)}
                  className="mt-1 accent-blue-600 cursor-pointer"
                />

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{typeInfo.icon}</span>
                        <span className="font-medium text-gray-800 text-sm">{typeInfo.label}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                          item.priority === 'CRITICAL' ? 'bg-red-100 text-red-700' :
                          item.priority === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                          item.priority === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {item.priority}
                        </span>
                      </div>

                      {item.prompt_text && (
                        <p className="text-sm text-gray-600 mt-1 italic">&ldquo;{item.prompt_text}&rdquo;</p>
                      )}

                      {product && (
                        <div className="flex items-center gap-3 mt-1.5 text-xs">
                          <span className="font-mono text-gray-500">{product.ergalyon_code}</span>
                          <span className="text-gray-600 truncate">{product.description}</span>
                        </div>
                      )}

                      {/* Payload details */}
                      {item.payload_json && item.payload_json.options && (
                        <div className="mt-2 space-y-1">
                          {item.payload_json.options.map((opt: string, i: number) => (
                            <label key={i} className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer hover:text-gray-800">
                              <input type="radio" name={`opt-${item.id}`} className="accent-blue-600" />
                              {opt}
                            </label>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="flex-shrink-0 text-right">
                      <div className="text-xs text-gray-400 mb-2">
                        {new Date(item.created_at).toLocaleDateString('el-GR', {
                          day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
                        })}
                      </div>

                      {/* Actions (only for open/in_progress) */}
                      {filter !== 'resolved' && (
                        <div className="flex gap-1.5">
                          <button
                            onClick={() => handleResolve(item.id, 'approved')}
                            disabled={isResolving}
                            className="px-2.5 py-1 text-xs bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors disabled:opacity-50 font-medium"
                          >
                            {isResolving ? '...' : 'Έγκριση'}
                          </button>
                          <button
                            onClick={() => handleResolve(item.id, 'edited')}
                            disabled={isResolving}
                            className="px-2.5 py-1 text-xs bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors disabled:opacity-50 font-medium"
                          >
                            Επεξεργασία
                          </button>
                          <button
                            onClick={() => handleResolve(item.id, 'rejected')}
                            disabled={isResolving}
                            className="px-2.5 py-1 text-xs bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors disabled:opacity-50 font-medium"
                          >
                            Απόρριψη
                          </button>
                        </div>
                      )}

                      {item.status === 'resolved' && (
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          item.resolution === 'approved' ? 'bg-green-100 text-green-700' :
                          item.resolution === 'rejected' ? 'bg-red-100 text-red-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {item.resolution === 'approved' ? 'Εγκρίθηκε' :
                           item.resolution === 'rejected' ? 'Απορρίφθηκε' : 'Επεξεργάστηκε'}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Pagination hint */}
      {total > 50 && (
        <div className="mt-4 text-center text-sm text-gray-400">
          Εμφανίζονται 50 από {total} — χρησιμοποίησε φίλτρα για μικρότερα σύνολα
        </div>
      )}
    </DashboardLayout>
  )
}