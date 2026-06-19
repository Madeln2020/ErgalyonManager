'use client'

import Link from 'next/link'
import DashboardLayout from '../DashboardLayout'

export default function SettingsPage() {
  return (
    <DashboardLayout>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Ρυθμίσεις</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-800 mb-3">Categories</h3>
          <p className="text-sm text-gray-500">Manage K1/K2/K3 hierarchy</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-800 mb-3">Users</h3>
          <p className="text-sm text-gray-500">Manage user accounts</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-800 mb-3">Supplier Rules</h3>
          <p className="text-sm text-gray-500">Preview and test rules (§8.4)</p>
        </div>
        <Link href="/settings/rag">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 cursor-pointer hover:bg-gray-50">
            <h3 className="font-semibold text-gray-800 mb-3">Supplier Agreement Q&A (RAG)</h3>
            <p className="text-sm text-gray-500">Ask questions about supplier agreements</p>
          </div>
        </Link>
      </div>
    </DashboardLayout>
  )
}