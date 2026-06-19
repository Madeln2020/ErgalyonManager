'use client'

import { useState } from 'react'
import DashboardLayout from '../DashboardLayout'

export default function ExportPage() {
  const [format, setFormat] = useState('csv')

  const handleExport = async () => {
    const url = `/api/v1/export?format=${format}`
    window.open(url, '_blank')
  }

  return (
    <DashboardLayout>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Export</h2>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 max-w-lg">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Μορφή εξαγωγής</label>
          <div className="flex gap-3">
            {['csv', 'json', 'excel', 'xml'].map((f) => (
              <button
                key={f}
                onClick={() => setFormat(f)}
                className={`px-4 py-2 rounded-lg text-sm border transition-colors ${
                  format === f
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                }`}
              >
                .{f}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleExport}
          className="w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 mt-2"
        >
          📤 Εξαγωγή
        </button>
      </div>
    </DashboardLayout>
  )
}
