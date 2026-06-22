// frontend/src/app/enrichment/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { EnrichmentEvent as EnrichmentEventType, EnrichmentQueueItem, Product } from '@/lib/types'

interface EnrichmentTriggerForm {
  product_id: string
  source: string
  enrichment_level: string
}

export default function EnrichmentPage() {
  const { token } = useAuth()
  const [products, setProducts] = useState<Product[]>([])
  const [events, setEvents] = useState<EnrichmentEventType[]>([])
  const [queueItems, setQueueItems] = useState<EnrichmentQueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [form, setForm] = useState<EnrichmentTriggerForm>({
    product_id: '',
    source: 'all',
    enrichment_level: '',
  })

  // Fetch data
  useEffect(() => {
    if (!token) return
    setLoading(true)

    Promise.all([
      apiFetch<Product[]>('/api/v1/products'),
      apiFetch<EnrichmentEventType[]>('/api/v1/enrichment'),
    ])
      .then(([productsData, eventsData]) => {
        setProducts(productsData)
        setEvents(eventsData)
        setLoading(false)
      })
      .catch((err) => {
        console.error('Failed to fetch enrichment data:', err)
        setLoading(false)
      })
  }, [token])

  // Trigger enrichment for a product
  const handleTrigger = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.product_id) return

    setTriggering(true)
    try {
      await apiFetch('/api/v1/enrichment/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: form.product_id,
          source: form.source || 'all',
          enrichment_level: form.enrichment_level || undefined,
        }),
      })
      // Refresh events
      const eventsData = await apiFetch<EnrichmentEventType[]>('/api/v1/enrichment')
      setEvents(eventsData)
      alert('Enrichment triggered successfully!')
    } catch (err) {
      console.error('Failed to trigger enrichment:', err)
      alert('Failed to trigger enrichment: ' + (err as Error).message)
    } finally {
      setTriggering(false)
    }
  }

  // Get status badge color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PENDING':
        return 'bg-yellow-100 text-yellow-800'
      case 'PROCESSING':
        return 'bg-blue-100 text-blue-800'
      case 'COMPLETED':
        return 'bg-green-100 text-green-800'
      case 'FAILED':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  // Get source label
  const getSourceLabel = (source: string | null) => {
    if (!source) return 'All'
    const labels: { [key: string]: string } = {
      xml: 'XML',
      catalog: 'Catalog',
      product_list: 'Product List',
      manual: 'Manual',
      web_scraping: 'Web Scraping',
      all: 'All',
    }
    return labels[source] || source
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Enrichment Pipeline</h1>

      {/* Trigger Form */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Trigger Enrichment</h2>
        <form onSubmit={handleTrigger} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Product</label>
            <select
              value={form.product_id}
              onChange={(e) => setForm({ ...form, product_id: e.target.value })}
              className="w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              required
            >
              <option value="">Select a product</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.canonical_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Source</label>
            <select
              value={form.source}
              onChange={(e) => setForm({ ...form, source: e.target.value })}
              className="w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All</option>
              <option value="xml">XML</option>
              <option value="catalog">Catalog</option>
              <option value="product_list">Product List</option>
              <option value="manual">Manual</option>
              <option value="web_scraping">Web Scraping</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Level (optional)</label>
            <select
              value={form.enrichment_level}
              onChange={(e) => setForm({ ...form, enrichment_level: e.target.value })}
              className="w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Levels</option>
              <option value="XML">XML</option>
              <option value="CATALOG">Catalog</option>
              <option value="PRODUCT_LIST">Product List</option>
              <option value="MANUAL">Manual</option>
              <option value="WEB_SCRAPING">Web Scraping</option>
            </select>
          </div>

          <div className="md:col-span-3">
            <button
              type="submit"
              disabled={triggering || !form.product_id}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-300"
            >
              {triggering ? 'Triggering...' : 'Trigger Enrichment'}
            </button>
          </div>
        </form>
      </div>

      {/* Enrichment Events */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Enrichment Events</h2>
        </div>

        {loading ? (
          <div className="p-6 text-center text-gray-500">Loading...</div>
        ) : events.length === 0 ? (
          <div className="p-6 text-center text-gray-500">No enrichment events yet</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Product
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source
                  </th>
                  <th className="px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Changes
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Applied At
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {events.map((event) => (
                  <tr key={event.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {event.product_id.slice(0, 8)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {event.source_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {event.changes_json ? (
                        <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-32">
                          {JSON.stringify(event.changes_json, null, 2)}
                        </pre>
                      ) : (
                        'No changes'
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {event.applied_at ? new Date(event.applied_at).toLocaleString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
