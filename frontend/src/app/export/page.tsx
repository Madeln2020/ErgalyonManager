// frontend/src/app/export/page.tsx
'use client'

import { useState, useEffect } from 'react'
import DashboardLayout from '../DashboardLayout'
import { apiFetch } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function ExportPage() {
  const { token } = useAuth()
  const [format, setFormat] = useState<'csv' | 'json' | 'xlsx'>('csv')
  const [pylonCompatible, setPylonCompatible] = useState(false)
  const [supplierId, setSupplierId] = useState<string | null>(null)
  const [categoryK1Id, setCategoryK1Id] = useState<string | null>(null)
  const [dateFrom, setDateFrom] = useState<string | null>(null)
  const [dateTo, setDateTo] = useState<string | null>(null)
  const [suppliers, setSuppliers] = useState<Array<{id: string; name: string}>>([])
  const [categories, setCategories] = useState<Array<{id: string; name: string}>>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Fetch suppliers for dropdown
    apiFetch<Array<{id: string; name: string}>>('/suppliers')
      .then(data => setSuppliers(data))
      .catch(err => {
        console.error('Failed to fetch suppliers:', err)
      })
  }, [])

  useEffect(() => {
    // Fetch categories (k1) for dropdown
    // Assuming there is an endpoint for categories, maybe /api/v1/categories
    // If not, we might need to create it or skip for now.
    // For now, we'll leave categories empty.
    // TODO: Implement categories endpoint if needed.
  }, [])

  const handleExport = async () => {
    if (!token) {
      alert('Please log in to export data')
      return
    }

    setLoading(true)
    const params = new URLSearchParams()
    params.append('format', format)
    if (pylonCompatible) params.append('pylon_compatible', 'true')
    if (supplierId) params.append('supplier_id', supplierId)
    if (categoryK1Id) params.append('category_k1_id', categoryK1Id)
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)

    // Build the URL
    const url = `/api/v1/export?${params.toString()}`

    // Since the export endpoint returns a file (StreamingResponse), we want to download it
    // We'll use fetch directly to handle the blob
    try {
      const res = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error?.message || `HTTP ${res.status}`)
      }
      const blob = await res.blob()
      const filename = `export_${new Date().toISOString().slice(0,19).replace(/[:T]/g,'_')}.${format}`
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename
      link.click()
      window.URL.revokeObjectURL(downloadUrl)
    } catch (err) {
      console.error('Export failed:', err)
      alert('Export failed: ' + (err instanceof Error ? err.message : String(err)))
    } finally {
      setLoading(false)
    }
  }

  return (
    <DashboardLayout>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Export</h2>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 max-w-2xl">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Μορφή εξαγωγής</label>
          <div className="flex gap-3">
            {['csv', 'json', 'xlsx'].map((f) => (
              <button
                key={f}
                onClick={() => setFormat(f as 'csv' | 'json' | 'xlsx')}
                className={`px-4 py-2 rounded-lg text-sm border transition-colors ${
                  format === f
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                }`}
              >
                .{f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-6">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between md:gap-6">
            {/* Supplier Filter */}
            <div className="w-full md:w-1/3">
              <label className="block text-sm font-medium text-gray-700 mb-2">Προμηθευτής</label>
              <select
                value={supplierId ?? ''}
                onChange={e => setSupplierId(e.target.value || null)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Όλοι</option>
                {suppliers.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            {/* Category Filter */}
            <div className="w-full md:w-1/3">
              <label className="block text-sm font-medium text-gray-700 mb-2">Κατηγορία (Κ1)</label>
              <select
                value={categoryK1Id ?? ''}
                onChange={e => setCategoryK1Id(e.target.value || null)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Όλες</option>
                {categories.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            {/* Date Range */}
            <div className="w-full md:w-1/3">
              <div className="flex gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Από</label>
                  <input
                    type="date"
                    value={dateFrom ?? ''}
                    onChange={e => setDateFrom(e.target.value || null)}
                    className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Εώς</label>
                  <input
                    type="date"
                    value={dateTo ?? ''}
                    onChange={e => setDateTo(e.target.value || null)}
                    className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mb-4">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <input
              type="checkbox"
              checked={pylonCompatible}
              onChange={e => setPylonCompatible(e.target.checked)}
              className="h-4 w-4 text-blue-600 border-gray-300 rounded"
            />
            Εξαγωγή σε formato Pylon ERP (συμβατό)
          </label>
        </div>

        <button
          onClick={handleExport}
          disabled={loading}
          className={`w-full py-3 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center justify-center gap-2 ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? '⏳ Εξαγωγή...' : '📤 Εξαγωγή'}
        </button>
      </div>
    </DashboardLayout>
  )
}