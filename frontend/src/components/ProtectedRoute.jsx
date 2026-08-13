import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children, requireRole }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 text-center text-[var(--color-ink-soft)]">
        Loading…
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />

  if (requireRole && user.role !== requireRole) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 text-center text-[var(--color-ink-soft)]">
        This page is only available to {requireRole}s.
      </div>
    )
  }

  return children
}
