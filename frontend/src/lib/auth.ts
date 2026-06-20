// frontend/src/lib/auth.ts
import { useState, useEffect } from 'react'

const TOKEN_KEY = '***'

export function getToken(): string | null {
  return typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
}

export function setToken(token: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, token)
  }
}

export function removeToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY)
  }
}

// Simple hook to manage auth state
export function useAuth() {
  const [token, setInternalToken] = useState<string | null>(null)
  const [user, setUser] = useState<any | null>(null) // TODO: Define User interface
  const [loading, setLoading] = useState<boolean>(true) // To avoid flashing UI on initial load

  useEffect(() => {
    const storedToken = getToken()
    if (storedToken) {
      setInternalToken(storedToken)
      // Fetch user info from API
      fetchUser(storedToken)
    } else {
      setLoading(false)
    }
  }, [])

  const fetchUser = async (token: string) => {
    try {
      // First, try to decode token to get basic info (optimistic update)
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        setUser({
          id: payload.sub,
          email: payload.email || '',
          role: payload.role || 'USER',
          organization_id: payload.organization_id || '',
        })
      } catch (e) {
        console.warn('Could not decode token, will fetch from API', e)
      }

      // Then fetch from API for authoritative data
      const res = await fetch('/api/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      if (res.ok) {
        const userData = await res.json()
        setUser(userData)
      } else {
        // If me endpoint fails, clear token and user
        removeToken()
        setInternalToken(null)
        setUser(null)
      }
    } catch (err) {
      console.error('Failed to fetch user:', err)
      removeToken()
      setInternalToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const login = async (newToken: string) => {
    setToken(newToken)
    setInternalToken(newToken)
    await fetchUser(newToken)
  }

  const logout = () => {
    removeToken()
    setInternalToken(null)
    setUser(null)
  }

  return { token, user, login, logout, isAuthenticated: !!token, loading }
}
