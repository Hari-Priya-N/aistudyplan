import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, setToken, getToken } from '../lib/api'

const AuthContext = createContext(null)

const HEARTBEAT_MS = 60_000

// Where each role lands after signing in.
export function homePathFor(user) {
  if (!user) return '/login'
  if (user.role === 'management') return '/management'
  if (user.role === 'instructor') return '/faculty'
  return '/'
}

export const ROLE_LABEL = { student: 'Student', instructor: 'Faculty', management: 'Management' }

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return null
    }
    try {
      const me = await api.me()
      setUser(me)
      return me
    } catch {
      setToken(null)
      setUser(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  // Activity tracking: while a tab is open and visible, ping the backend once a
  // minute so sessions and time-on-platform are measured.
  useEffect(() => {
    if (!user) return undefined
    const beat = () => {
      if (document.visibilityState === 'visible') api.heartbeat().catch(() => {})
    }
    beat()
    const id = setInterval(beat, HEARTBEAT_MS)
    document.addEventListener('visibilitychange', beat)
    return () => {
      clearInterval(id)
      document.removeEventListener('visibilitychange', beat)
    }
  }, [user])

  const login = async (identifier, password) => {
    const res = await api.login({ email: identifier, password })
    setToken(res.access_token)
    return refreshUser()
  }

  const signup = async ({ email, password, full_name, role }) => {
    const res = await api.signup({ email, password, full_name, role })
    setToken(res.access_token)
    return refreshUser()
  }

  const logout = () => {
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
