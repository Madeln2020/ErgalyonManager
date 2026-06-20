// frontend/src/app/dashboard/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'
import { useAuth } from '@/lib/auth'

interface Stats {
  products: number
  suppliers: number
  reviewOpen: number
  reviewHigh: number
  invoices: number
}
interface RecentProduct {
  id: string
  ergalyon_code: string
  description: string
  current_price: number | null
  created_at: string
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100 animate-pulse">
      <div className="flex items-center justify-between mb-2">
        <div className="w-8 h-8 bg-gray-200 rounded" />
        <div className="w-10 h-10 bg-gray-200 rounded-lg" />
      </div>
      <div className="h-7 w-16 bg-gray-200 rounded mb-1" />
      <div className="h-4 w-24 bg-gray-200 rounded" />
    </div>
  )
}

function SkeletonRow() {
  return (
    <div className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg animate-pulse">
      <div className="flex items-center gap-3">
        <div className="h-4 w-24 bg-gray-200 rounded" />
        <div className="h-4 w-48 bg-gray-200 rounded" />
      </div>
      <div className="h-4 w-16 bg-gray-200 rounded" />
    </div>
  )
}

export default function DashboardPage() {
  const { token, user, isAuthenticated, loading: authLoading } = useAuth()
  const [stats, setStats] = useState<Stats>({ products: 0, suppliers: 0, reviewOpen: 0, reviewHigh: 0, invoices: 0 })
  const [recent, setRecent] = useState<RecentProduct[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Only fetch data if we have a token
    if (!token) {
      setLoading(false)
      return
    }

    Promise.all([
      apiFetch<{ total: number }>('/api/v1/products?limit=1'),
      apiFetch<any[]>('/api/v1/suppliers'),
      apiFetch<{ total: number }>('/api/v1/review-queue?status=open&limit=1'),
      apiFetch<{ total: number }>('/api/v1/review-queue?status=open&priority=HIGH&limit=1'),
      apiFetch<{ items: RecentProduct[] }>('/api/v1/products?limit=5'),
    ]).then(([products, suppliers, review, reviewHigh, recentProds]) => {
      setStats({
        products: products.total || 0,
        suppliers: Array.isArray(suppliers) ? suppliers.length : 0,
        reviewOpen: review.total || 0,
        reviewHigh: reviewHigh.total || 0,
        invoices: 0, // We don't have an invoices count endpoint yet
      })
      setRecent(recentProds.items || [])
      setLoading(false)
    }).catch(err => {
      console.error('Failed to fetch dashboard data:', err)
      setLoading(false)
    })
  }, [token]) // Re-fetch when token changes

  const cards = [
    { label: 'Προϊόντα', value: stats.products, icon: '🔧', color: 'bg-blue-500' },
    { label: 'Προμηθευτές', value: stats.suppliers, icon: '🏢', color: 'bg-green-500' },
    { label: 'Ουρά Ελέγχου', value: stats.reviewOpen, icon: '🔍', color: stats.reviewOpen > 0 ? 'bg-orange-500' : 'bg-gray-400' },
    { label: 'Υψηλής Προτεραιότητας', value: stats.reviewHigh, icon: '⚠️', color: stats.reviewHigh > 0 ? 'bg-red-500' : 'bg-gray-400' },
  ]

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Πίνακας Ελέγχου</h2>

      {/* Quick actions row */}
      <div className="flex flex-wrap gap-2 mb-6">
        <a href="/upload" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          ↑ Ανέβασμα Αρχείου
        </a>
        <a href="/review" className="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors">
          🔍 Ουρά Ελέγχου {stats.reviewOpen > 0 && `(${stats.reviewOpen})`}
        </a>
        <a href="/products" className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors">
          📦 Προϊόντα
        </a>
        <a href="/export" className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors">
          📤 Export
        </a>
        <a href="/scrape" className="px-4 py-2 bg-gray-600 text-white rounded-lg text-sm font-medium hover:bg-gray-700 transition-colors">
          🕸 Scraping
        </a>
      </div>

      {/* Stats cards with skeleton */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {cards.map((card) => (
            <div key={card.label} className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
              <div className="flex items-center justify-between mb-2">
                <span className="text-2xl">{card.icon}</span>
                <div className={`w-10 h-10 ${card.color} rounded-lg flex items-center justify-center text-white text-sm font-bold opacity-80`}>
                  {card.value}
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900">{card.value}</p>
              <p className="text-sm text-gray-500 mt-0.5">{card.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Recent products */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
        <h3 className="font-semibold text-gray-800 mb-3">📋 Πρόσφατα Προϊόντα</h3>
        {loading ? (
          <div className="space-y-2">
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </div>
        ) : recent.length === 0 ? (
          <div className="text-center py-6 text-gray-400 text-sm">Δεν υπάρχουν προϊόντα ακόμα</div>
        ) : (
          <div className="space-y-2">
            {recent.map((p) => (
              <div key={p.id} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="font-mono text-xs text-blue-600 flex-shrink-0">{p.ergalyon_code}</span>
                  <span className="text-sm text-gray-800 truncate">{p.description}</span>
                </div>
                <span className="sm font-mono text-gray-600 flex-shrink-0">
                  {p.current_price ? `${Number(p.current_price).toFixed(2)}€` : '—'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Workflow */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-semibold text-gray-800 mb-3">Βασική ροή εργασίας</h3>
        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
          <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full">1. Ανέβασμα</span>
          <span>→</span>
          <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full">2. Parse</span>
          <span>→</span>
          <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full">3. Review</span>
          <span>→</span>
          <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full">4. Προϊόντα</span>
          <span>→</span>
          <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full">5. Export</span>
        </div>
      </div>
    </div>
  )
}