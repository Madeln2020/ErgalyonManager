// frontend/src/app/upload/page.tsx
'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import DashboardLayout from '../DashboardLayout'
import { apiFetch } from '@/lib/api'
import { useAuth } from '@/lib/auth'

interface Supplier { id: string; name: string; is_active: boolean }
interface Invoice {
  id: string
  file_format: string
  status: string
  parsing_confidence: number | null
  total_amount: number | null
  error_message: string | null
  created_at: string
  queued?: boolean
}
interface CatalogSpec {
  name: string
  supplier_code: string
  description: string
  price: number
  currency: string
  image_url: string
  source_file: string
}
interface UploadResult {
  invoices: Invoice[]
  job_id: string
}
interface CatalogResult {
  specs: CatalogSpec[]
  confidence: number
}
type UploadStatus = 'idle' | 'uploading' | 'done' | 'error'

export default function UploadPage() {
  const { token, user } = useAuth()
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [selectedSupplier, setSelectedSupplier] = useState('')
  const [docType, setDocType] = useState('invoice')
  const [files, setFiles] = useState<File[]>([])
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle')
  const [uploadResults, setUploadResults] = useState<Invoice[]>([])
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [resultsExpanded, setResultsExpanded] = useState<Set<string>>(new Set())
  // Catalog-specific state
  const [catalogSpecs, setCatalogSpecs] = useState<CatalogSpec[]>([])
  const [catalogConfidence, setCatalogConfidence] = useState<number>(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Fetch active suppliers
    if (!token) return
    apiFetch<Supplier[]>('/suppliers')
      .then(data => {
        const activeSuppliers = data.filter((s: Supplier) => s.is_active)
        setSuppliers(activeSuppliers)
        if (activeSuppliers.length > 0) setSelectedSupplier(activeSuppliers[0].id)
      })
      .catch(err => {
        console.error('Failed to fetch suppliers:', err)
        // Don't set error state to avoid cluttering UI, just log
      })
  }, [token])

  const getTypeFromFile = (name: string): string => {
    const ext = name.split('.').pop()?.toLowerCase()
    if (ext === 'xml') return 'xml'
    if (ext === 'pdf') return 'pdf'
    if (ext === 'csv') return 'excel'
    if (ext === 'xlsx' || ext === 'xls') return 'excel'
    if (ext === 'jpg' || ext === 'jpeg' || ext === 'png' || ext === 'webp') return 'image'
    return 'unknown'
  }

  const getTypeLabel = (format: string) => {
    switch (format) {
      case 'xml': return { icon: '📄', label: 'XML (myDATA)' }
      case 'pdf': return { icon: '📕', label: 'PDF' }
      case 'excel': return { icon: '📊', label: 'Excel/CSV' }
      case 'image': return { icon: '🖼️', label: 'Εικόνα' }
      default: return { icon: '📎', label: format }
    }
  }

  const getStatusBadge = (status: string, queued?: boolean) => {
    if (queued) return 'text-orange-600 bg-orange-50'
    switch (status) {
      case 'uploaded': return 'text-blue-600 bg-blue-50'
      case 'parsing': return 'text-yellow-600 bg-yellow-50'
      case 'parsed': return 'text-indigo-600 bg-indigo-50'
      case 'normalized': return 'text-purple-600 bg-purple-50'
      case 'enriched': return 'text-green-600 bg-green-50'
      case 'reviewed': return 'text-emerald-600 bg-emerald-50'
      case 'failed': return 'text-red-600 bg-red-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  // Reset catalog results when docType changes
  useEffect(() => {
    setCatalogSpecs([])
    setCatalogConfidence(0)
    setUploadResults([])
    setUploadStatus('idle')
    setUploadError(null)
  }, [docType])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setUploadError(null)
    setUploadStatus('idle')
    setUploadResults([])
    setCatalogSpecs([])
    const dropped = Array.from(e.dataTransfer.files)
    setFiles(prev => [...prev, ...dropped])
  }, [])

  const removeFile = (idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx))
    if (files.length <= 1) {
      setUploadResults([])
      setCatalogSpecs([])
      setUploadStatus('idle')
      setUploadError(null)
    }
  }

  const handleUpload = async () => {
    if (!selectedSupplier || files.length === 0) return

    setUploadStatus('uploading')
    setUploadError(null)
    setUploadResults([])
    setCatalogSpecs([])

    try {
      const formData = new FormData()
      formData.append('supplier_id', selectedSupplier)
      formData.append('document_type', docType)
      files.forEach(f => formData.append('files', f))

      // Choose endpoint based on document type
      const endpoint = docType === 'catalog'
        ? '/api/v1/catalogs/upload'
        : '/api/v1/invoices/upload'

      const res = await apiFetch<any>(endpoint, {
        method: 'POST',
        body: formData,
        // Note: We don't set Content-Type here because FormData needs to set it
        // our apiFetch will not override Content-Type if it's already set by the browser
      })

      if (docType === 'catalog') {
        const data: CatalogResult = res
        setCatalogSpecs(data.specs || [])
        setCatalogConfidence(data.confidence || 0)
        setUploadStatus('done')
      } else {
        const data: UploadResult = res
        setUploadResults(data.invoices || [])

        const failures = (data.invoices || []).filter(i => i.status === 'failed')
        if (failures.length > 0) {
          setUploadStatus('error')
        }
      }
    } catch (err: any) {
      setUploadError(err.message)
      setUploadStatus('error')
    }
  }

  return (
    <DashboardLayout>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">
        {docType === 'catalog' ? 'Ανέβασμα Καταλόγου (Vision)' : 'Ανέβασμα Τιμολογίων'}
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Controls */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          {/* Supplier selector */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Προμηθευτής</label>
            <select
              value={selectedSupplier}
              onChange={e => setSelectedSupplier(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {suppliers.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          {/* Doc type */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Τύπος</label>
            <div className="flex gap-3 flex-wrap">
              {[
                { key: 'invoice', label: 'Τιμολόγιο' },
                { key: 'offer', label: 'Προσφορά' },
                { key: 'catalog', label: 'Κατάλογος (Vision)' },
              ].map(t => (
                <label key={t.key} className="flex items-center gap-1.5 text-sm cursor-pointer">
                  <input
                    type="radio" name="doc_type"
                    className="accent-blue-600"
                    checked={docType === t.key}
                    onChange={() => setDocType(t.key)}
                  />
                  {t.label}
                </label>
              ))}
            </div>
          </div>

          {/* Drop zone */}
          <div
            onDragOver={e => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center hover:border-blue-400 transition-colors cursor-pointer"
          >
            <div className="text-4xl mb-3">{docType === 'catalog' ? '🖼️' : '📁'}</div>
            <p className="text-sm text-gray-600">Σύρετε αρχεία εδώ ή κάντε κλικ</p>
            <p className="text-xs text-gray-400 mt-1">
              {docType === 'catalog' ? 'JPG, PNG, PDF (catalog)' : 'PDF, XML, JPG, PNG, XLSX, CSV'}
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              accept={docType === 'catalog' ? '.jpg,.jpeg,.png,.pdf' : undefined}
              onChange={e => {
                const selected = Array.from(e.target.files || [])
                setFiles(prev => [...prev, ...selected])
              }}
            />
          </div>

          {/* File list */}
          {files.length > 0 && (
            <div className="mt-4 space-y-1.5 max-h-52 overflow-y-auto">
              {files.map((f, i) => {
                const type = getTypeFromFile(f.name)
                const { icon } = getTypeLabel(type)
                const result = uploadResults[i]
                return (
                  <div key={i} className="flex items-center justify-between bg-gray-50 border border-gray-100 px-3 py-2 rounded-lg text-sm group">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-base flex-shrink-0">{icon}</span>
                      <span className="truncate text-xs">{f.name}</span>
                      <span className="text-xs text-gray-400 flex-shrink-0">{type.toUpperCase()}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {result ? (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(result.status, result.queued)}`}>
                          {result.queued ? '⏳ Σε Αναθεώρηση' : result.status === 'enriched' ? '✅ OK' : result.status}
                        </span>
                      ) : uploadStatus === 'uploading' ? (
                        <span className=\"text-blue-500 text-xs\">⏳</span>
                      ) : null}
                      <button
                        onClick={e => { e.stopPropagation(); removeFile(i) }}
                        className=\"text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity\"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
              })}\n",
  "file_size": 16972,
  "truncated": true,
  "is_binary": false,
  "is_image": false
}