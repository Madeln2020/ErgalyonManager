// frontend/src/app/layout.tsx
'use client'

import type { Metadata } from 'next'
import { Inter, Manrope } from 'next/font/google'
import './globals.css'
import { MantineProvider } from '@mantine/core'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'

const font = Manrope({ subsets: ['greek', 'latin'] })

export const metadata: Metadata = {
  title: 'EDM v2 — Ergalyon Data Manager',
  description: 'Διαχείριση δεδομένων προϊόντων & εργαλείων',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, logout, loading, isAuthenticated } = useAuth()
  const router = useRouter()

  const handleLogout = async () => {
    logout()
    // Optionally clear token from backend via API call if needed
    // await apiFetch('/auth/logout', { method: 'POST' })
    router.refresh() // Re-render to show login button
  }

  // Redirect to login if not authenticated and not on login page
  useEffect(() => {
    if (!loading && !isAuthenticated && !window.location.pathname.startsWith('/login')) {
      router.push('/login')
    }
  }, [loading, isAuthenticated, router])

  // If loading auth state, show a loading indicator
  if (loading) {
    return (
      <html lang="el" className="h-full">
        <body className={`${font.className} h-full bg-gray-50 flex items-center justify-center`}>
          <div className="text-lg text-gray-600">Φόρτωση...</div>
        </body>
      </html>
    )
  }

  return (
    <html lang="el" className="h-full">
      <body className={`${font.className} h-full bg-gray-50`}>
        {!loading && isAuthenticated && (
          <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16 items-center">
                {/* Logo and Nav */} 
                <div className="flex items-center flex-1 min-w-0">
                  <div className="flex-shrink-0 mr-6">
                    <img className="h-10 w-10" src="/logo.png" alt="EDM v2" />
                  </div>
                  <nav className="hidden md:flex items-baseline space-x-4 min-w-0 overflow-x-auto">
                    <NavLink href="/" label="Αρχική" />
                    <NavLink href="/products" label="Προϊόντα" />
                    <NavLink href="/suppliers" label="Προμηθευτές" />
                    <NavLink href="/export" label="Εξαγωγή" />
                    <NavLink href="/review" label="Έλεγχος" />
                    <NavLink href="/enrichment" label="Ενίσχυση" />
                  </nav>
                </div>
                {/* User Info & Logout */} 
                <div className="flex items-center">
                  {user ? (
                    <div className="flex items-center ml-4">
                      <div className="flex-shrink-0 mr-3">
                        <img
                          className="h-10 w-10 rounded-full"
                          src="https://via.placeholder.com/10"
                          alt="User Avatar"
                        />
                      </div>
                      <div className="hidden md:block">
                        <div className="text-sm font-medium text-gray-800">{user.display_name || user.email}</div>
                        <div className="text-xs font-medium text-gray-500">
                          {user.role} · {user.organization_id?.slice(0, 8)}...
                        </div>
                      </div>
                      <button
                        onClick={handleLogout}
                        className="ml-4 flex h-9 items-center rounded-md bg-white border border-gray-300 px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
                      >
                        Αποσύνδεση
                      </button>
                    </div>
                  ) : (
                    <a
                      href="/login"
                      className="ml-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                    >
                      Σύνδεσμος
                    </a>
                  )}
                </div>
              </div>
            </div>
          </header>
        )}
        <main className="container mx-auto px-4 py-8 md:px-6 lg:px-8">
          {children}
        </main>
      </body>
    </html>
  )
}

// Helper component for navigation links
function NavLink({ href, label }: { href: string; label: string }) {
  const currentPath = window.location.pathname
  const isActive = currentPath === href

  return (
    <a
      href={href}
      className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive
        ? 'bg-blue-600 text-white'
        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
      }`}
    >
      {label}
    </a>
  )
}
