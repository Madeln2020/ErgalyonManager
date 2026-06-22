'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { clsx } from 'clsx'

const navItems = [
  { href: '/', label: 'Πίνακας Ελέγχου', icon: '📊' },
  { href: '/upload', label: 'Ανέβασμα', icon: '📁' },
  { href: '/matching', label: 'Αντιστοίχιση', icon: '🔗' },
  { href: '/products', label: 'Προϊόντα', icon: '🔧' },
  { href: '/suppliers', label: 'Προμηθευτές', icon: '🏢' },
  { href: '/enrichment', label: 'Enrichment', icon: '✨' },
  { href: '/review', label: 'Ουρά Ελέγχου', icon: '🔍' },
  { href: '/costs', label: 'Κόστος', icon: '💰' },
  { href: '/export', label: 'Export', icon: '📤' },
  { href: '/settings', label: 'Ρυθμίσεις', icon: '⚙️' },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 bg-gray-800 text-white flex flex-col h-screen fixed left-0 top-0">
      <div className="p-5 border-b border-gray-700">
        <h1 className="text-xl font-bold tracking-tight">EDM v2.1</h1>
        <p className="text-xs text-gray-400 mt-1">Ergalyon Data Manager</p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
              pathname === item.href || pathname.startsWith(item.href + '/')
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-700 hover:text-white'
            )}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        v2.1.0 · Εργαλύων
      </div>
    </aside>
  )
}
