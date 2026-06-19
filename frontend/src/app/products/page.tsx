'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '../DashboardLayout'

interface Product {
  id: string
  ergalyon_code: string
  supplier_code: string
  manufacturer_code: string | null
  ean: string | null
  description: string
  current_price: number | null
  manufacturer_flag: boolean
  supplier_id: string
  created_at: string
}
interface Supplier { id: string; name: string }

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [supplierFilter, setSupplierFilter] = useState('')
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [page, setPage] = useState(0)
  const limit = 25

  useEffect(() => {
    fetch('/api/v1/suppliers')
      .then(r => r.json())
      .then(data => setSuppliers(Array.isArray(data) ? data : []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ limit: String(limit), offset: String(page * limit) })
    if (search) params.set('search', search)
    if (supplierFilter) params.set('supplier_id', supplierFilter)

    fetch(`/api/v1/products?${params.toString()}`)
      .then(r => r.json())
      .then(data => {
        setProducts(data.items || [])
        setTotal(data.total || 0)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [search, supplierFilter, page])

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Προϊόντα</h2>
        <span className="text-sm text-gray-500">{total} σύνολο</span>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        {/* Filters */}
        <div className="p-4 border-b border-gray-100 flex gap-3">
          <input
            type="text"
            placeholder="🔍 Αναζήτηση: κωδικός / περιγραφή / EAN..."
            className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0) }}
          />
          <select
            value={supplierFilter}
            onChange={e => { setSupplierFilter(e.target.value); setPage(0) }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Όλοι οι προμηθευτές</option>
            {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-gray-600">Κωδ. Εργαλ.</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Περιγραφή</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Κωδ. Προμηθευτή</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Κωδ. Κατασκευαστή</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Τιμή</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Σημαία</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-center py-8 text-gray-400">Φόρτωση...</td></tr>
              ) : products.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-8 text-gray-400">Δεν βρέθηκαν προϊόντα</td></tr>
              ) : products.map((p) => (
                <tr key={p.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-blue-600 text-xs">{p.ergalyon_code}</td>
                  <td className="px-4 py-3 text-gray-800 max-w-xs truncate">{p.description}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{p.supplier_code}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{p.manufacturer_code || <span className="text-orange-400">—</span>}</td>
                  <td className="px-4 py-3 text-right font-mono text-sm">
                    {p.current_price ? `${Number(p.current_price).toFixed(2)}€` : '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {p.manufacturer_flag ? (
                      <span className="text-green-500 text-xs">✅</span>
                    ) : (
                      <span className="text-gray-300 text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > limit && (
          <div className="p-4 border-t border-gray-100 flex items-center justify-between text-sm">
            <span className="text-gray-500">
              {page * limit + 1}–{Math.min((page + 1) * limit, total)} από {total}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
              >
                ← Προηγούμενο
              </button>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={(page + 1) * limit >= total}
                className="px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
              >
                Επόμενο →
              </button>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}