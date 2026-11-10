import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, homePathFor } from '../context/AuthContext'
import { api, ApiError } from '../lib/api'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [demo, setDemo] = useState(false)

  useEffect(() => {
    api.publicConfig().then((c) => setDemo(!!c.demo)).catch(() => {})
  }, [])

  const onSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const me = await login(email.trim(), password)
      navigate(homePathFor(me))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 sm:px-6 py-16">
      <h1 className="text-3xl font-semibold mb-2">Welcome back</h1>
      <p className="text-[var(--color-ink-soft)] mb-8">Sign in to pick up where you left off.</p>

      <form onSubmit={onSubmit} className="card p-6 flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Email or roll number
          <input
            type="text"
            autoComplete="username"
            required
            className="input-field"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@school.edu or 22AD001"
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Password
          <input
            type="password"
            required
            className="input-field"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </label>

        {error && <p className="text-sm text-[var(--color-rust)]">{error}</p>}

        <button type="submit" disabled={submitting} className="btn-primary py-2.5 mt-2">
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      {demo && (
        <div className="card p-4 mt-6 text-sm">
          <p className="font-semibold mb-2">Demo accounts · password <span className="font-[var(--font-mono)]">Demo@1234</span></p>
          <div className="flex flex-wrap gap-2">
            {[
              ['Student', 'student@demo.edu'],
              ['Faculty', 'lakshmi@demo.edu'],
              ['Management', 'admin@demo.edu'],
            ].map(([label, mail]) => (
              <button
                key={mail}
                type="button"
                className="btn-secondary px-3 py-1.5 text-xs"
                onClick={() => {
                  setEmail(mail)
                  setPassword('Demo@1234')
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      <p className="text-sm text-[var(--color-ink-soft)] mt-6 text-center">
        New here?{' '}
        <Link to="/signup" className="text-[var(--color-indigo)] font-medium">
          Create an account
        </Link>
      </p>
    </div>
  )
}
