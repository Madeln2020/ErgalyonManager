// frontend/src/lib/api.ts
import { getToken, removeToken } from './auth'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1'

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = getToken()
  
  // Start with base headers
  const headers: HeadersInit = new Headers()
  
  // Add Authorization if token exists
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  
  // Merge with user-provided headers (user headers take precedence)
  const mergedHeaders = new Headers(headers)
  if (options?.headers) {
    Object.entries(options.headers).forEach(([key, value]) => {
      mergedHeaders.set(key, value as string)
    })
  }
  
  const mergedOptions: RequestInit = {
    ...options,
    headers: mergedHeaders,
  }

  const res = await fetch(`${API_BASE}${path}`, mergedOptions)

  // If unauthorized, clear token and maybe redirect (handled by caller or component)
  if (res.status === 401) {
    removeToken()
    // Optionally, you could redirect to login here, but we don't have a login page yet
    // For now, we'll let the error propagate and let components handle it
  }

  if (!res.ok) {
    // Try to parse as JSON, fallback to text
    let err: { error: { message: string } } | string
    try {
      err = await res.json()
    } catch {
      err = await res.text()
    }
    const message = typeof err === 'string' 
      ? err 
      : err.error?.message || `HTTP ${res.status}`
    throw new Error(message)
  }
  
  // For most endpoints, we expect JSON response
  // If the response is not JSON (e.g., file download), this will throw
  // Callers should handle non-JSON responses separately if needed
  return res.json()
}
