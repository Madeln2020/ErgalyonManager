'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '../../DashboardLayout'

interface Supplier { id: string; name: string; is_active: boolean }
interface RagResponse { answer: string; context: string[] }

export default function RagPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [selectedSupplier, setSelectedSupplier] = useState<string>('')
  const [question, setQuestion] = useState<string>('')
  const [answer, setAnswer] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Fetch active suppliers
    fetch('/api/v1/suppliers')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) {
          setSuppliers(data.filter((s: Supplier) => s.is_active))
          if (data.length > 0) setSelectedSupplier(data[0].id)
        }
      })
      .catch(() => {
        setError('Failed to load suppliers')
      })
  }, [])

  const handleAsk = async () => {
    if (!selectedSupplier || !question.trim()) {
      setError('Please select a supplier and enter a question')
      return
    }
    setLoading(true)
    setError(null)
    setAnswer('')
    try {
      const resp = await fetch('/api/v1/rag/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          supplier_id: selectedSupplier,
          question: question.trim(),
        }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(err.detail || `HTTP ${resp.status}`)
      }
      const data: RagResponse = await resp.json()
      setAnswer(data.answer)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <DashboardLayout>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Supplier Agreement Q&A (RAG)</h2>

      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Supplier</label>
            <select
              value={selectedSupplier}
              onChange={e => setSelectedSupplier(e.target.value)}
              disabled={loading}
              className={`w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${loading && 'opacity-80'}`}
            >
              {suppliers.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Question</label>
            <textarea
              value={question}
              onChange={e => setQuestion(e.target.value)}
              rows={3}
              placeholder="Ask about the supplier agreement (e.g., payment terms, delivery conditions, penalties)"
              disabled={loading}
              className={`w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${loading && 'opacity-80'}`}
            />
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleAsk}
              disabled={loading || !selectedSupplier || !question.trim()}
              className={`px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors ${loading && 'opacity-80'}`}
            >
              {loading ? 'Asking...' : 'Ask Question'}
            </button>
          </div>

          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              Error: {error}
            </div>
          )}

          {answer && (
            <div className="mt-4">
              <h3 className="font-semibold text-gray-800 mb-2">Answer</h3>
              <div className="bg-gray-50 p-4 rounded-lg text-gray-700 whitespace-pre-wrap">
                {answer}
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}