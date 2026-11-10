import { Navigate } from 'react-router-dom'
import { useAuth, homePathFor } from '../context/AuthContext'

// requireRole: a role string or an array of allowed roles.
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

  const allowed = requireRole ? [].concat(requireRole) : null
  if (allowed && !allowed.includes(user.role)) {
    return <Navigate to={homePathFor(user)} replace />
  }

  return children
}
