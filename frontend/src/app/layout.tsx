import type { Metadata } from 'next'
import { Inter, Manrope } from 'next/font/google'
import './globals.css'
import { MantineProvider } from '@mantine/core'

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
  return (
    <html lang="el" className="h-full">
      <body className={`${font.className} h-full bg-gray-50`}>
        <MantineProvider>{children}</MantineProvider>
      </body>
    </html>
  )
}
