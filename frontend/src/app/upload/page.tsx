'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import DashboardLayout from '../DashboardLayout'

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
    fetch('/api/v1/suppliers')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) {
          setSuppliers(data.filter((s: Supplier) => s.is_active))
          if (data.length > 0) setSelectedSupplier(data[0].id)
        }
      })
      .catch(() => {})
  }, [])

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

      const res = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(err.detail?.[0]?.msg || `HTTP ${res.status}`)
      }

      if (docType === 'catalog') {
        const data: CatalogResult = await res.json()
        setCatalogSpecs(data.specs || [])
        setCatalogConfidence(data.confidence || 0)
        setUploadStatus('done')
      } else {
        const data: UploadResult = await res.json()
        setUploadResults(data.invoices || [])
        setUploadStatus('done')

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
            <label className="block text-sm font-medium text-gray-700 mb-1">Προμηθευτής</label>
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
            <label className="block text-sm font-medium text-gray-700 mb-1">Τύπος</label>
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
                        <span className="text-blue-500 text-xs">⏳</span>
                      ) : null}
                      <button
                        onClick={e => { e.stopPropagation(); removeFile(i) }}
                        className="text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Upload button */}
          <button
            onClick={handleUpload}
            disabled={files.length === 0 || !selectedSupplier || uploadStatus === 'uploading'}
            className="mt-4 w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {uploadStatus === 'uploading'
              ? '⏳ Ανέβασμα...'
              : `📤 Ανέβασμα ${files.length > 0 ? `(${files.length} αρχείο${files.length > 1 ? 'α' : ''})` : ''}`
            }
          </button>

          {uploadError && (
            <div className="mt-3 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              Σφάλμα: {uploadError}
            </div>
          )}
        </div>

        {/* Right: Results panel */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          {docType === 'catalog' ? (
            /* ── Catalog Vision Results ── */
            <>
              <h3 className="font-semibold text-gray-800 mb-3">
                Αποτελέσματα Vision Καταλόγου
                {catalogSpecs.length > 0 && (
                  <span className="ml-2 text-xs text-gray-400 font-normal">({catalogSpecs.length} προϊόντα)</span>
                )}
              </h3>

              {uploadStatus === 'idle' && files.length === 0 && (
                <div className="text-center py-12 text-gray-400 text-sm">
                  <div className="text-4xl mb-3">🖼️</div>
                  <p>Επιλέξτε εικόνα καταλόγου</p>
                  <p className="text-xs text-gray-300 mt-1">Τα προϊόντα θα εμφανιστούν εδώ</p>
                </div>
              )}

              {uploadStatus === 'uploading' && (
                <div className="text-center py-12 text-blue-500 text-sm">
                  <div className="animate-pulse text-4xl mb-3">🔍</div>
                  <p>Γίνεται OCR & Vision ανάλυση...</p>
                </div>
              )}

              {catalogSpecs.length > 0 && (
                <>
                  {/* Confidence badge */}
                  <div className="mb-3 flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      catalogConfidence >= 0.9 ? 'text-green-600 bg-green-50' :
                      catalogConfidence >= 0.7 ? 'text-yellow-600 bg-yellow-50' :
                      'text-red-600 bg-red-50'
                    }`}>
                      Confidence: {(catalogConfidence * 100).toFixed(1)}%
                    </span>
                  </div>

                  {/* Specs table */}
                  <div className="overflow-x-auto max-h-[500px] overflow-y-auto border border-gray-100 rounded-lg">
                    <table className="min-w-full text-xs">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Όνομα</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Κωδικός</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Περιγραφή</th>
                          <th className="px-3 py-2 text-right font-medium text-gray-600">Τιμή</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Εικόνα</th>
                        </tr>
                      </thead>
                      <tbody>
                        {catalogSpecs.map((spec, i) => (
                          <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                            <td className="px-3 py-2 font-medium text-gray-800">{spec.name}</td>
                            <td className="px-3 py-2 text-gray-600">{spec.supplier_code}</td>
                            <td className="px-3 py-2 text-gray-500 max-w-[200px] truncate">{spec.description}</td>
                            <td className="px-3 py-2 text-right font-mono text-green-700">
                              {spec.price.toFixed(2)}€
                            </td>
                            <td className="px-3 py-2">
                              <a
                                href={spec.image_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 underline hover:text-blue-800"
                              >
                                View
                              </a>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Success message */}
                  <div className="mt-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
                    ✅ Ο κατάλογος αναλύθηκε! Βρέθηκαν {catalogSpecs.length} προϊόντα.
                  </div>
                </>
              )}

              {uploadStatus === 'done' && catalogSpecs.length === 0 && (
                <div className="mt-4 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg text-sm">
                  ⚠️ Δεν βρέθηκαν προϊόντα στον κατάλογο.
                </div>
              )}
            </>
          ) : (
            /* ── Standard Invoice Results ── */
            <>
              <h3 className="font-semibold text-gray-800 mb-3">
                Λεπτομέρειες Επεξεργασίας
                {uploadResults.length > 0 && (
                  <span className="ml-2 text-xs text-gray-400 font-normal">({uploadResults.length} αρχεία)</span>
                )}
              </h3>

              {uploadStatus === 'idle' && files.length === 0 && (
                <div className="text-center py-12 text-gray-400 text-sm">
                  <div className="text-4xl mb-3">📦</div>
                  <p>Επιλέξτε αρχεία και πατήστε "Ανέβασμα"</p>
                  <p className="text-xs text-gray-300 mt-1">Τα αποτελέσματα θα εμφανιστούν εδώ</p>
                </div>
              )}

              {uploadResults.length > 0 && (
                <div className="space-y-2 max-h-[500px] overflow-y-auto">
                  {uploadResults.map((inv, i) => {
                    const type = getTypeLabel(inv.file_format)
                    const isExpanded = resultsExpanded.has(inv.id)
                    return (
                      <div key={inv.id} className="border border-gray-100 rounded-lg overflow-hidden">
                        <button
                          onClick={() => {
                            const next = new Set(resultsExpanded)
                            if (next.has(inv.id)) next.delete(inv.id); else next.add(inv.id)
                            setResultsExpanded(next)
                          }}
                          className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-gray-50 transition-colors text-left"
                        >
                          <div className="flex items-center gap-2">
                            <span>{type.icon}</span>
                            <span className="text-xs font-medium text-gray-700">{files[i]?.name || type.label}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(inv.status, inv.queued)}`}>
                              {inv.status}
                            </span>
                            <span className="text-gray-400 text-xs">{isExpanded ? '▲' : '▼'}</span>
                          </div>
                        </button>
                        {isExpanded && (
                          <div className="px-3 pb-3 pt-1 border-t border-gray-50 bg-gray-50/50 space-y-1.5 text-xs">
                            <div className="flex justify-between">
                              <span className="text-gray-500">ID:</span>
                              <span className="font-mono text-gray-700">{inv.id.slice(0, 8)}...</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-500">Format:</span>
                              <span>{inv.file_format.toUpperCase()}</span>
                            </div>
                            {inv.parsing_confidence != null && (
                              <div className="flex justify-between">
                                <span className="text-gray-500">Confidence:</span>
                                <span className="font-mono font-medium">{(inv.parsing_confidence * 100).toFixed(1)}%</span>
                              </div>
                            )}
                            {inv.total_amount != null && (
                              <div className="flex justify-between">
                                <span className="text-gray-500">Total:</span>
                                <span className="font-mono font-medium text-green-700">{Number(inv.total_amount).toFixed(2)}€</span>
                              </div>
                            )}
                            <div className="flex justify-between">
                              <span className="text-gray-500">Created:</span>
                              <span className="font-mono text-gray-600">{new Date(inv.created_at).toLocaleString('el-GR')}</span>
                            </div>
                            {inv.error_message && (
                              <div className="bg-red-50 text-red-700 px-2 py-1 rounded text-xs">
                                Σφάλμα: {inv.error_message}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              {uploadStatus === 'done' && uploadResults.every(i => i.status === 'enriched') && (
                <div className="mt-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
                  ✅ Όλα τα αρχεία επεξεργάστηκαν με επιτυχία!
                </div>
              )}

              {uploadResults.length > 0 && (
                <div className="mt-4 grid grid-cols-3 gap-2">
                  {[
                    { label: 'Επιτυχία', count: uploadResults.filter(i => i.status === 'enriched').length, color: 'text-green-600 bg-green-50' },
                    { label: 'Σε εξέλιξη', count: uploadResults.filter(i => !['enriched', 'failed'].includes(i.status)).length, color: 'text-yellow-600 bg-yellow-50' },
                    { label: 'Αποτυχία', count: uploadResults.filter(i => i.status === 'failed').length, color: 'text-red-600 bg-red-50' },
                  ].map(stat => (
                    <div key={stat.label} className={`text-center px-2 py-2 rounded-lg ${stat.color}`}>
                      <div className="text-lg font-bold">{stat.count}</div>
                      <div className="text-xs">{stat.label}</div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}