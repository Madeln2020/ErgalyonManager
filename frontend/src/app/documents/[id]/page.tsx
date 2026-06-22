'use client'

import React, { useEffect, useState } from 'react'
import DashboardLayout from '@/app/DashboardLayout'
import { apiFetch } from '@/lib/api'
import { useRouter } from 'next/navigation'

interface ParsedDocument {
  id: string
  doc_kind: string
  parse_status: string
  confidence_score: number
  parser_version: string
  header_json: Record<string, any>
}

interface ParsedLineItem {
  id: string
  line_index: number
  supplier_sku_raw: string
  description_raw: string
  qty: number
  unit_price: number
  line_total: number
  extraction_source: string
  extraction_notes: string
  match_decision?: {
    product_id: string | null
    decision_type: string
    status: string
  }
}

export default function DocumentReviewPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [doc, setDoc] = useState<ParsedDocument | null>(null)
  const [lines, setLines] = useState<ParsedLineItem[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editedDesc, setEditedDesc] = useState('')
  const [saving, setSaving] = useState(false)
  const [triggering, setTriggering] = useState(false)

  useEffect(() => {
    fetchData()
  }, [params.id])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [docRes, linesRes] = await Promise.all([
        apiFetch<any>(`/api/v1/parsed-documents/${params.id}`),
        apiFetch<any>(`/api/v1/parsed-documents/${params.id}/lines`),
      ])
      setDoc(docRes)
      // Backend may return { lines: [...] } or just [...]
      setLines(Array.isArray(linesRes) ? linesRes : (linesRes.lines || []))
    } catch (e) {
      console.error('Failed to fetch document', e)
    } finally {
      setLoading(false)
    }
  }

  const saveDescription = async (id: string) => {
    setSaving(true)
    try {
      await apiFetch(`/api/v1/parsed-documents/${params.id}/lines/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description_raw: editedDesc }),
      })
      setLines(lines.map((l) => (l.id === id ? { ...l, description_raw: editedDesc } : l)))
      setEditingId(null)
    } catch (e) {
      console.error('Failed to save', e)
      alert('Σφάλμα αποθήκευσης')
    } finally {
      setSaving(false)
    }
  }

  const triggerMatching = async () => {
    setTriggering(true)
    try {
      await apiFetch('/api/v1/matching/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parsed_document_id: params.id }),
      })
      await fetchData()
      alert('Αντιστοίχιση ολοκληρώθηκε')
    } catch (e) {
      console.error('Matching failed', e)
      alert('Σφάλμα αντιστοίχισης')
    } finally {
      setTriggering(false)
    }
  }

  const isLowConfidence = (line: ParsedLineItem) => {
    // Low confidence if extraction_notes mentions low confidence or notes is empty
    return (
      (line.extraction_notes && line.extraction_notes.toLowerCase().includes('low'))
    )
  }

  const getConfidenceColor = (line: ParsedLineItem) => {
    if (isLowConfidence(line)) return 'bg-yellow-50 hover:bg-yellow-100'
    return ''
  }

  const getMatchBadge = (decision: ParsedLineItem['match_decision']) => {
    if (!decision) return <span className="text-xs text-gray-400">—</span>
    const colors: Record<string, string> = {
      auto_exact: 'bg-green-100 text-green-800',
      auto_suggested: 'bg-yellow-100 text-yellow-800',
      manual_confirm: 'bg-blue-100 text-blue-800',
      manual_override: 'bg-purple-100 text-purple-800',
    }
    return (
      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${colors[decision.decision_type] || 'bg-gray-100'}`}>
        {decision.decision_type?.replace(/_/g, ' ') || '—'}
      </span>
    )
  }

  return (
    <DashboardLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="text-gray-500 hover:text-gray-700 text-sm"
            >
              ← Πίσω
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Αναθεώρηση Εγγράφου</h1>
              {doc && (
                <p className="text-sm text-gray-500 mt-1">
                  {doc.doc_kind} · {doc.parse_status} · {doc.confidence_score !== null ? `${Math.round(doc.confidence_score * 100)}%` : 'N/A'}
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={triggerMatching}
              disabled={triggering}
              className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {triggering ? '⏳' : '🔗'} {triggering ? 'Αντιστοίχιση...' : 'Αντιστοίχιση'}
            </button>
          </div>
        </div>

        {/* Document Header Card */}
        {doc && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">📄 Στοιχεία Εγγράφου</h2>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Τύπος', value: doc.doc_kind },
                { label: 'Κατάσταση', value: doc.parse_status },
                { label: 'Εμπιστοσύνη', value: doc.confidence_score !== null ? `${Math.round(doc.confidence_score * 100)}%` : '—' },
                { label: 'Parser', value: doc.parser_version || '—' },
              ].map((item) => (
                <div key={item.label}>
                  <p className="text-xs font-medium text-gray-500">{item.label}</p>
                  <p className="text-sm font-semibold text-gray-900 capitalize">{item.value}</p>
                </div>
              ))}
            </div>
            {doc.header_json && Object.keys(doc.header_json).length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-xs font-medium text-gray-500 mb-1">Header Data</p>
                <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto">
                  {JSON.stringify(doc.header_json, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Lines Table */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-800">
              Γραμμές Εγγράφου ({lines.length})
            </h2>
          </div>

          {loading ? (
            <div className="p-12 text-center">
              <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <p className="mt-3 text-sm text-gray-500">Φόρτωση...</p>
            </div>
          ) : lines.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              <p className="text-4xl mb-2">📭</p>
              <p>Δεν βρέθηκαν γραμμές</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Περιγραφή</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ποσότητα</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Τιμή Μον.</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Σύνολο</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Πηγή</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Αντιστοίχιση</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ενέργεια</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {lines.map((line: ParsedLineItem) => (
                    <tr key={line.id} className={getConfidenceColor(line)}>
                      <td className="px-4 py-3 text-xs text-gray-400">{line.line_index}</td>
                      <td className="px-4 py-3 text-xs font-mono text-gray-700">{line.supplier_sku_raw || '—'}</td>
                      <td className="px-4 py-3 max-w-xs">
                        {editingId === line.id ? (
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={editedDesc}
                              onChange={(e) => setEditedDesc(e.target.value)}
                              className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs"
                              autoFocus
                            />
                            <button
                              onClick={() => saveDescription(line.id)}
                              disabled={saving}
                              className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                            >
                              💾
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded"
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <span
                            className="text-sm text-gray-900 cursor-pointer hover:text-blue-600"
                            onClick={() => {
                              setEditingId(line.id)
                              setEditedDesc(line.description_raw || '')
                            }}
                          >
                            {line.description_raw || <span className="text-gray-400 italic">Κενό</span>}
                            {isLowConfidence(line) && (
                              <span className="ml-1 text-xs bg-yellow-100 text-yellow-800 px-1 rounded">⚠️ χαμηλή εμπιστοσύνη</span>
                            )}
                          </span>
                        )}
                        {line.extraction_notes && (
                          <p className="text-xs text-gray-400 mt-0.5 truncate">{line.extraction_notes}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-gray-700">{line.qty ?? '—'}</td>
                      <td className="px-4 py-3 text-right text-sm text-gray-700">
                        {line.unit_price != null ? `${Number(line.unit_price).toFixed(2)}€` : '—'}
                      </td>
                      <td className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                        {line.line_total != null ? `${Number(line.line_total).toFixed(2)}€` : '—'}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {line.extraction_source || '—'}
                      </td>
                      <td className="px-4 py-3">
                        {getMatchBadge(line.match_decision)}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => {
                            setEditingId(line.id)
                            setEditedDesc(line.description_raw || '')
                          }}
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          ✏️
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}