'use client'

import { useEffect, useState, useCallback } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import DashboardLayout from '../DashboardLayout'

// ── Types ──
interface Supplier {
  id: string
  name: string
  vat_number: string | null
  country: string
  contact_email: string | null
  contact_phone: string | null
  rules_json: Record<string, any>
  parsing_profile: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

interface SupplierForm {
  name: string
  vat_number: string
  contact_email: string
  contact_phone: string
  parsing_profile: string
  rules_json: string
}

const emptyForm: SupplierForm = {
  name: '',
  vat_number: '',
  contact_email: '',
  contact_phone: '',
  parsing_profile: 'auto',
  rules_json: '{}',
}

const RULE_PRESETS: Record<string, string> = {
  'Ποιμενίδης (03- prefix)': JSON.stringify({
    code_normalization: [
      { operations: [{ op: 'strip_prefix', prefix: '03-' }, { op: 'trim' }], description: 'Poimenidis: 03-12345 → 12345' },
    ],
    validation: [{ field: 'normalized_supplier_code', rules: [{ required: true }, { regex: '^[0-9]+$' }] }],
    enrichment_hint: { manufacturer_code_source: 'scraping', scrape_url_template: 'https://www.poimenidis.gr/search?q={supplier_code}' },
  }, null, 2),
  'Κενό (no rules)': '{}',
  'Γενικός (uppercase + trim)': JSON.stringify({
    code_normalization: [
      { operations: [{ op: 'uppercase' }, { op: 'trim' }], description: 'Uppercase + trim' },
    ],
  }, null, 2),
}

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<SupplierForm>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [testDialogOpen, setTestDialogOpen] = useState(false)
  const [testInput, setTestInput] = useState('')
  const [testResult, setTestResult] = useState<{ normalized_code: string; confidence: number; rules_applied: any[]; validation_errors: string[] } | null>(null)
  const [testLoading, setTestLoading] = useState(false)

  const showToast = useCallback((type: 'success' | 'error', message: string) => {
    setToast({ type, message })
    setTimeout(() => setToast(null), 4000)
  }, [])

  const fetchSuppliers = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/v1/suppliers')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setSuppliers(Array.isArray(data) ? data : [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchSuppliers() }, [fetchSuppliers])

  const openAdd = () => {
    setEditingId(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  const openEdit = (s: Supplier) => {
    setEditingId(s.id)
    setForm({
      name: s.name,
      vat_number: s.vat_number || '',
      contact_email: s.contact_email || '',
      contact_phone: s.contact_phone || '',
      parsing_profile: s.parsing_profile || 'auto',
      rules_json: JSON.stringify(s.rules_json || {}, null, 2),
    })
    setDialogOpen(true)
  }

  const applyPreset = (key: string) => {
    const val = RULE_PRESETS[key]
    if (val) setForm(f => ({ ...f, rules_json: val }))
  }

  const handleTestRules = async () => {
    let parsedRules: Record<string, any> = {}
    try {
      parsedRules = JSON.parse(form.rules_json)
    } catch {
      showToast('error', 'Το rules_json δεν είναι έγκυρο JSON')
      return
    }
    if (!testInput.trim()) {
      showToast('error', 'Βάλε ένα δείγμα κωδικού προϊόντος')
      return
    }
    setTestLoading(true)
    setTestResult(null)
    try {
      const res = await fetch('/api/v1/rules/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rules_json: parsedRules,
          sample_code: testInput.trim(),
          sample_description: 'Δείγμα προϊόντος για δοκιμή',
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setTestResult(data)
    } catch (err: any) {
      showToast('error', 'Σφάλμα δοκιμής: ' + err.message)
    } finally {
      setTestLoading(false)
    }
  }

  const handleSave = async () => {
    // Basic validation
    if (!form.name.trim()) {
      showToast('error', 'Το όνομα προμηθευτή είναι υποχρεωτικό')
      return
    }
    let parsedRules: Record<string, any> = {}
    try {
      parsedRules = JSON.parse(form.rules_json)
    } catch {
      showToast('error', 'Το rules_json δεν είναι έγκυρο JSON')
      return
    }

    setSaving(true)
    try {
      const body = {
        name: form.name.trim(),
        vat_number: form.vat_number.trim() || null,
        contact_email: form.contact_email.trim() || null,
        contact_phone: form.contact_phone.trim() || null,
        parsing_profile: form.parsing_profile || 'auto',
        rules_json: parsedRules,
      }

      let res: Response
      if (editingId) {
        res = await fetch(`/api/v1/suppliers/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
      } else {
        res = await fetch('/api/v1/suppliers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
      }

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail?.[0]?.msg || `HTTP ${res.status}`)
      }

      showToast('success', editingId ? 'Ο προμηθευτής ενημερώθηκε' : 'Ο προμηθευτής δημιουργήθηκε')
      setDialogOpen(false)
      await fetchSuppliers()
    } catch (err: any) {
      showToast('error', err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Είσαι σίγουρος ότι θέλεις να απενεργοποιήσεις αυτόν τον προμηθευτή;')) return
    setDeletingId(id)
    try {
      const res = await fetch(`/api/v1/suppliers/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      showToast('success', 'Ο προμηθευτής απενεργοποιήθηκε')
      await fetchSuppliers()
    } catch (err: any) {
      showToast('error', err.message)
    } finally {
      setDeletingId(null)
    }
  }

  // ── Render ──
  return (
    <DashboardLayout>
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all ${
          toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {toast.message}
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Προμηθευτές</h2>
        <button onClick={openAdd} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          + Νέος Προμηθευτής
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          Σφάλμα φόρτωσης: {error}
          <button onClick={fetchSuppliers} className="ml-3 underline">Δοκίμασε ξανά</button>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left px-4 py-3 font-medium text-gray-600">Όνομα</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">ΑΦΜ</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Προφίλ</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Κανόνες</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Κατάσταση</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Ενέργειες</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">Φόρτωση...</td></tr>
            ) : suppliers.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">Δεν υπάρχουν προμηθευτές</td></tr>
            ) : suppliers.map((s) => (
              <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium">{s.name}</td>
                <td className="px-4 py-3 text-gray-600 font-mono text-xs">{s.vat_number || '—'}</td>
                <td className="px-4 py-3 text-gray-600 text-xs">{s.contact_email || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    s.parsing_profile === 'xml' ? 'bg-green-100 text-green-700' :
                    s.parsing_profile === 'pdf' ? 'bg-purple-100 text-purple-700' :
                    s.parsing_profile === 'excel' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{s.parsing_profile || 'auto'}</span>
                </td>
                <td className="px-4 py-3">
                  {s.rules_json && Object.keys(s.rules_json).length > 0 ? (
                    <span className="text-xs text-gray-500">{Object.keys(s.rules_json).join(', ')}</span>
                  ) : (
                    <span className="text-xs text-gray-400">—</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1 text-xs font-medium ${
                    s.is_active ? 'text-green-600' : 'text-red-500'
                  }`}>
                    <span className={`w-2 h-2 rounded-full ${s.is_active ? 'bg-green-500' : 'bg-red-400'}`} />
                    {s.is_active ? 'Ενεργός' : 'Ανενεργός'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => openEdit(s)} className="text-blue-600 hover:text-blue-800 text-xs font-medium mr-3">
                    Επεξεργασία
                  </button>
                  {s.is_active && (
                    <button
                      onClick={() => handleDelete(s.id)}
                      disabled={deletingId === s.id}
                      className="text-red-500 hover:text-red-700 text-xs font-medium disabled:opacity-50"
                    >
                      {deletingId === s.id ? '...' : 'Απενεργοποίηση'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add / Edit Dialog */}
      <Dialog.Root open={dialogOpen} onOpenChange={setDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-40" />
          <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-2xl z-50 max-h-[85vh] overflow-y-auto">
            <Dialog.Title className="text-lg font-bold text-gray-800 mb-1">
              {editingId ? 'Επεξεργασία Προμηθευτή' : 'Νέος Προμηθευτής'}
            </Dialog.Title>
            <Dialog.Description className="text-sm text-gray-500 mb-5">
              {editingId ? 'Ενημέρωσε τα στοιχεία του προμηθευτή' : 'Συμπλήρωσε τα στοιχεία του νέου προμηθευτή'}
            </Dialog.Description>

            <div className="space-y-4">
              {/* Row: Name + VAT */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Όνομα *</label>
                  <input
                    type="text" value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g. Ποιμενίδης Α.Ε."
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">ΑΦΜ</label>
                  <input
                    type="text" value={form.vat_number}
                    onChange={e => setForm(f => ({ ...f, vat_number: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g. 094012345"
                  />
                </div>
              </div>

              {/* Row: Email + Phone */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email" value={form.contact_email}
                    onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Τηλέφωνο</label>
                  <input
                    type="text" value={form.contact_phone}
                    onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              {/* Parsing profile */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Προφίλ Parsing</label>
                <select
                  value={form.parsing_profile}
                  onChange={e => setForm(f => ({ ...f, parsing_profile: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="auto">Auto-detect</option>
                  <option value="xml">XML (myDATA)</option>
                  <option value="pdf">PDF</option>
                  <option value="excel">Excel/CSV</option>
                </select>
              </div>

              {/* Rules JSON */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-medium text-gray-700">Κανόνες (rules_json)</label>
                  <div className="flex gap-1">
                    {Object.keys(RULE_PRESETS).map(key => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => applyPreset(key)}
                        className="px-2 py-0.5 bg-gray-100 hover:bg-gray-200 text-xs text-gray-600 rounded transition-colors"
                      >
                        {key}
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  value={form.rules_json}
                  onChange={e => setForm(f => ({ ...f, rules_json: e.target.value }))}
                  rows={8}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder='{"code_normalization": [...]}'
                />
                <div className="flex items-center justify-between mt-1">
                  <p className="text-xs text-gray-400">JSON με κανόνες κανονικοποίησης, validation, enrichment_hint</p>
                  <button
                    type="button"
                    onClick={() => { setTestDialogOpen(true); setTestInput(''); setTestResult(null); }}
                    className="px-3 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-medium rounded transition-colors"
                  >
                    🧪 Δοκίμασε Κανόνες
                  </button>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-100">
              <Dialog.Close className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors">
                Ακύρωση
              </Dialog.Close>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {saving ? 'Αποθήκευση...' : editingId ? 'Ενημέρωση' : 'Δημιουργία'}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Rule Tester Dialog */}
      <Dialog.Root open={testDialogOpen} onOpenChange={setTestDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-40" />
          <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-lg z-50">
            <Dialog.Title className="text-lg font-bold text-gray-800 mb-1">🧪 Δοκιμή Κανόνων</Dialog.Title>
            <Dialog.Description className="text-sm text-gray-500 mb-4">
              Βάλε έναν κωδικό προϊόντος για να δεις πώς θα μετατραπεί από τους κανόνες
            </Dialog.Description>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Κωδικός προϊόντος</label>
                <input
                  type="text"
                  value={testInput}
                  onChange={e => setTestInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleTestRules() }}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g. 03-12345"
                />
              </div>

              <button
                onClick={handleTestRules}
                disabled={testLoading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
              >
                {testLoading ? 'Δοκιμή...' : '🧪 Δοκίμασε'}
              </button>

              {testResult && (
                <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Κανονικοποιημένος κωδικός:</span>
                    <span className="font-mono font-bold text-lg text-green-700">{testResult.normalized_code || '(κενό)'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Confidence:</span>
                    <span className="font-mono font-medium">{testResult.confidence}%</span>
                  </div>
                  {testResult.rules_applied.length > 0 && (
                    <div>
                      <p className="text-gray-600 mb-1">Κανόνες που εφαρμόστηκαν:</p>
                      {testResult.rules_applied.filter(r => r.triggered).map((r, i) => (
                        <div key={i} className="text-xs font-mono bg-white rounded px-2 py-1 border border-gray-100 mb-1">
                          <span className="text-blue-600">{r.rule_type}</span>:
                          "{r.input}" → "{r.output}"
                        </div>
                      ))}
                    </div>
                  )}
                  {testResult.validation_errors.length > 0 && (
                    <div className="bg-red-50 rounded px-3 py-2">
                      <p className="text-xs font-medium text-red-700 mb-1">Σφάλματα validation:</p>
                      {testResult.validation_errors.map((e, i) => (
                        <p key={i} className="text-xs text-red-600">• {e}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <Dialog.Close className="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
              ✕
            </Dialog.Close>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </DashboardLayout>
  )
}
