// /src/app/products/[id]/page.tsx
'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '../../DashboardLayout'
import { apiFetch } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import Link from 'next/link'

interface Product {
  id: string
  name: string
  code: string
  description: string
  category: string
  status: string
  ean: string | null
  manufacturer_code: string | null
}

interface SupplierLink {
  id: string
  supplier_name: string
  supplier_sku: string
  current_cost: number | null
  price_history_json: string // JSON string of array {cost, source, approved_at, approved_by}
}

interface PendingCost {
  id: string
  description: string
  amount: number
}

export default function ProductDetailPage({ params }: { params: { id: string } }) {
  const { token } = useAuth()
  const [product, setProduct] = useState<Product | null>(null)
  const [links, setLinks] = useState<SupplierLink[]>([])
  const [pending, setPending] = useState<PendingCost[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    setLoading(true)
    try {
      const prod = await apiFetch<Product>(`/api/v1/products/${params.id}`)
      setProduct(prod)
      const pl = await apiFetch<SupplierLink[]>(`/api/v1/product-supplier-links?product_id=${params.id}`)
      setLinks(pl)
      const pc = await apiFetch<PendingCost[]>(`/api/v1/costs?product_id=${params.id}&status=pending`)
      setPending(pc)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [params.id])

  const handleEnrich = async () => {
    if (!token) return alert('Login required')
    try {
      await apiFetch(`/api/v1/products/${params.id}/enrich`, { method: 'POST' })
      alert('Enrichment started')
    } catch (e) {
      console.error(e)
      alert('Enrichment failed')
    }
  }

  if (loading) return <DashboardLayout>Loading...</DashboardLayout>
  if (!product) return <DashboardLayout>Product not found</DashboardLayout>

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">{product.name}</h2>
        <Link href="/products" className="text-blue-600 hover:underline">← Back to list</Link>
      </div>

      {/* Canonical data */}
      <section className="grid grid-cols-2 gap-4 bg-white p-4 rounded shadow mb-6">
        <div><strong>Code:</strong> {product.code}</div>
        <div><strong>Description:</strong> {product.description}</div>
        <div><strong>Category:</strong> {product.category}</div>
        <div><strong>Status:</strong> {product.status}</div>
        <div><strong>EAN:</strong> {product.ean ?? '—'}</div>
        <div><strong>Manufacturer Code:</strong> {product.manufacturer_code ?? '—'}</div>
      </section>

      {/* Linked suppliers */}
      <section className="mb-6">
        <h3 className="text-xl font-semibold mb-2">Suppliers</h3>
        <table className="w-full text-sm bg-white rounded shadow">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">Supplier</th>
              <th className="px-4 py-2 text-left">Supplier SKU</th>
              <th className="px-4 py-2 text-right">Current Cost</th>
            </tr>
          </thead>
          <tbody>
            {links.map(l => (
              <tr key={l.id} className="border-t">
                <td className="px-4 py-2">{l.supplier_name}</td>
                <td className="px-4 py-2 font-mono text-xs">{l.supplier_sku}</td>
                <td className="px-4 py-2 text-right">{l.current_cost !== null ? `${l.current_cost.toFixed(2)} €` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Price history */}
      <section className="mb-6">
        <h3 className="text-xl font-semibold mb-2">Price History</h3>
        {links.map(l => {
          let history: Array<{cost:number; source:string; approved_at:string; approved_by:string}> = []
          try { history = JSON.parse(l.price_history_json) } catch (_) {}
          return (
            <div key={l.id} className="mb-4">
              <h4 className="font-medium">{l.supplier_name}</h4>
              <ul className="list-disc list-inside text-sm">
                {history.map((h, i) => (
                  <li key={i}>
                    {h.cost} € – {h.source} – {new Date(h.approved_at).toLocaleDateString()} by {h.approved_by}
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </section>

      {/* Enrichment suggestions */}
      <section className="mb-6">
        <button
          onClick={handleEnrich}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >Enrich Product</button>
      </section>

      {/* Pending cost updates */}
      <section className="mb-6">
        <h3 className="text-xl font-semibold mb-2">Pending Cost Updates</h3>
        {pending.length === 0 ? (
          <p className="text-gray-500">No pending costs.</p>
        ) : (
          <ul className="list-disc list-inside">
            {pending.map(p => (
              <li key={p.id}>{p.description}: {p.amount} €</li>
            ))}
          </ul>
        )}
      </section>
    </DashboardLayout>
  )
}
