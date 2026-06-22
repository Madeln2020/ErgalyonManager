// frontend/src/app/suppliers/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'
import { useAuth } from '@/lib/auth'

interface Supplier {
  id: string
  name: string
  vat_number: string | null
  default_currency: string
  rules_json: any
  is_active: boolean
  created_at: string
}

interface CodeNormalizationRule {
  op: string
  prefix?: string
  suffix?: string
  pattern?: string
  replacement?: string
}

interface ValidationRule {
  type: string
  min_length?: number
  max_length?: number
  required?: boolean
}

export default function SuppliersPage() {
  const { token } = useAuth()
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null)
  const [saving, setSaving] = useState(false)

  // Form state for rules editing
  const [codeRules, setCodeRules] = useState<CodeNormalizationRule[]>([])
  const [validationRules, setValidationRules] = useState<ValidationRule[]>([])

  useEffect(() => {
    if (!token) return
    setLoading(true)

    apiFetch('/api/v1/suppliers')
      .then((data: any) => {
        setSuppliers(Array.isArray(data) ? (data as Supplier[]) : [])
        setLoading(false)
      })
      .catch((err: any) => {
        console.error('Failed to fetch suppliers:', err)
        setLoading(false)
      })
  }, [token])

  const handleEdit = (supplier: Supplier) => {
    setEditingSupplier(supplier)
    const rules = supplier.rules_json || {}
    setCodeRules(rules.code_normalization || [])
    setValidationRules(rules.validation || [])
  }

  const handleSave = async () => {
    if (!editingSupplier) return

    setSaving(true)
    try {
      const updatedRules = {
        code_normalization: codeRules,
        validation: validationRules,
      }

      await apiFetch(`/api/v1/suppliers/${editingSupplier.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rules_json: updatedRules }),
      })

      // Refresh suppliers list
      const data = await apiFetch('/api/v1/suppliers')
      setSuppliers(Array.isArray(data) ? (data as Supplier[]) : [])
      setEditingSupplier(null)
      alert('Supplier rules saved successfully!')
    } catch (err: any) {
      console.error('Failed to save supplier rules:', err)
      alert('Failed to save rules: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  const addCodeRule = () => {
    setCodeRules([...codeRules, { op: 'strip_prefix' }])
  }

  const updateCodeRule = (index: number, field: string, value: any) => {
    const updated = [...codeRules]
    updated[index] = { ...updated[index], [field]: value }
    setCodeRules(updated)
  }

  const removeCodeRule = (index: number) => {
    setCodeRules(codeRules.filter((_: any, i: number) => i !== index))
  }

  const addValidationRule = () => {
    setValidationRules([...validationRules, { type: 'required' }])
  }

  const updateValidationRule = (index: number, field: string, value: any) => {
    const updated = [...validationRules]
    updated[index] = { ...updated[index], [field]: value }
    setValidationRules(updated)
  }

  const removeValidationRule = (index: number) => {
    setValidationRules(validationRules.filter((_: any, i: number) => i !== index))
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Suppliers</h1>

      {loading ? (
        <div className="text-center text-gray-500">Loading...</div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-800">Supplier List</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    VAT
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Currency
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {suppliers.map((supplier: Supplier) => (
                  <tr key={supplier.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {supplier.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {supplier.vat_number || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {supplier.default_currency}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          supplier.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {supplier.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <button
                        onClick={() => handleEdit(supplier)}
                        className="text-blue-600 hover:text-blue-900 font-medium"
                      >
                        Edit Rules
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit Rules Modal */}
      {editingSupplier && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-screen overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900">
                Edit Rules: {editingSupplier.name}
              </h3>
              <button
                onClick={() => setEditingSupplier(null)}
                className="text-gray-400 hover:text-gray-500"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Code Normalization Rules */}
              <div>
                <h4 className="text-md font-medium text-gray-900 mb-3">
                  Code Normalization Rules
                </h4>
                <div className="space-y-3">
                  {codeRules.map((rule: CodeNormalizationRule, idx: number) => (
                    <div
                      key={idx}
                      className="bg-gray-50 rounded-lg p-4 flex items-center gap-4"
                    >
                      <select
                        value={rule.op}
                        onChange={(e) => updateCodeRule(idx, 'op', e.target.value)}
                        className="border border-gray-300 rounded-md shadow-sm py-1 px-3 text-sm"
                      >
                        <option value="strip_prefix">Strip Prefix</option>
                        <option value="strip_suffix">Strip Suffix</option>
                        <option value="replace">Replace</option>
                        <option value="uppercase">Uppercase</option>
                        <option value="lowercase">Lowercase</option>
                      </select>

                      {rule.op === 'strip_prefix' || rule.op === 'strip_suffix' ? (
                        <input
                          type="text"
                          value={rule.prefix || ''}
                          onChange={(e) =>
                            updateCodeRule(idx, rule.op === 'strip_prefix' ? 'prefix' : 'suffix', e.target.value)
                          }
                          placeholder={rule.op === 'strip_prefix' ? 'Prefix to strip' : 'Suffix to strip'}
                          className="border border-gray-300 rounded-md shadow-sm py-1 px-3 text-sm flex-1"
                        />
                      ) : rule.op === 'replace' ? (
                        <>
                          <input
                            type="text"
                            value={rule.pattern || ''}
                            onChange={(e) => updateCodeRule(idx, 'pattern', e.target.value)}
                            placeholder="Pattern"
                            className="border border-gray-300 rounded-md shadow-sm py-1 px-3 text-sm flex-1"
                          />
                          <input
                            type="text"
                            value={rule.replacement || ''}
                            onChange={(e) => updateCodeRule(idx, 'replacement', e.target.value)}
                            placeholder="Replacement"
                            className="border border-gray-300 rounded-md shadow-sm py-1 px-3 text-sm flex-1"
                          />
                        </>
                      ) : null}

                      <button
                        onClick={() => removeCodeRule(idx)}
                        className="text-red-600 hover:text-red-900 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  onClick={addCodeRule}
                  className="mt-2 text-sm text-blue-600 hover:text-blue-900 font-medium"
                >
                  + Add Code Rule
                </button>
              </div>

              {/* Validation Rules */}
              <div>
                <h4 className="text-md font-medium text-gray-900 mb-3">
                  Validation Rules
                </h4>\n                {

 validationRules.map((rule: ValidationRule, idx: number) => (
                  <div
                    key={idx}
                    className="bg-gray-50 rounded-lg p-4 flex items-center gap-4 mb-3"
                  >
                    <select
                      value={rule.type}
                      onChange={(e) => updateValidationRule(idx, 'type', e.target.value)}
                      className="border border-gray-300 rounded-md shadow-sm py-1 px-3 text-sm"
                    >
                      <option value="required">Required</option>
                      <option value="min_length">Min Length</option>
                      <option value="max_length">Max Length</option>
                      <option value="pattern">Regex Pattern</option>
                    </select>

                    {rule.type === 'min_length' || rule.type === 'max_length' ? (
                      <input
                        type="number"
                        value={rule.min_length || rule.max_length || ''}
                        onChange={(e) =>
                          updateValidationRule(
                            idx,
                            rule.type === 'min_length' ? 'min_length' : 'max_length',
                            parseInt(e.target.value)
                          )
                        }
                        placeholder="Length"
                        className="border border-gray-300 rounded-md shadow-sm py-1 px-3 text-sm w-24"
                      />
                    ) : null}

                    <button
                      onClick={() => removeValidationRule(idx)}
                      className="text-red-600 hover:text-red-900 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ))}

                <button
                  onClick={addValidationRule}
                  className="mt-2 text-sm text-blue-600 hover:text-blue-900 font-medium"
                >
                  + Add Validation Rule
                </button>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-4">
              <button
                onClick={() => setEditingSupplier(null)}
                className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300"
              >
                {saving ? 'Saving...' : 'Save Rules'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
