// src/app/lib/MantineWrapper.tsx
'use client'

import { MantineProvider } from '@mantine/core'

export default function MantineWrapper({ children }: { children: React.ReactNode }) {
  return <MantineProvider>{children}</MantineProvider>
}