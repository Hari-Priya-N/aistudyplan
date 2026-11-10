import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, homePathFor } from '../context/AuthContext'
import { ApiError } from '../lib/api'

export default function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', password: '', role: 'student' })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const onSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const me = await signup(form)
      navigate(homePathFor(me))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 sm:px-6 py-16">
      <h1 className="text-3xl font-semibold mb-2">Start your path</h1>
      <p className="text-[var(--color-ink-soft)] mb-8">A few details and you're in.</p>

      <form onSubmit={onSubmit} className="card p-6 flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Full name
          <input required className="input-field" value={form.full_name} onChange={update('full_name')} placeholder="Ada Lovelace" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Email
          <input type="email" required className="input-field" value={form.email} onChange={update('email')} placeholder="you@school.edu" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Password
          <input type="password" required minLength={8} className="input-field" value={form.password} onChange={update('password')} placeholder="At least 8 characters" />
        </label>
        <fieldset className="flex flex-col gap-1.5 text-sm font-medium">
          <legend className="mb-1">I am a…</legend>
          <div className="flex gap-2">
            {[['student', 'Student'], ['faculty', 'Faculty']].map(([r, label]) => (
              <button
                type="button"
                key={r}
                onClick={() => setForm((f) => ({ ...f, role: r }))}
                className={`flex-1 py-2 rounded-md border text-sm capitalize transition-colors ${
                  form.role === r
                    ? 'border-[var(--color-indigo)] bg-[var(--color-indigo-tint)] text-[var(--color-indigo)] font-semibold'
                    : 'border-[var(--color-line)] text-[var(--color-ink-soft)]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="text-xs font-normal text-[var(--color-ink-soft)] mt-1">
            Students are usually registered by their faculty from an Excel sheet — sign in with your roll number if so.
          </span>
        </fieldset>

        {error && <p className="text-sm text-[var(--color-rust)]">{error}</p>}

        <button type="submit" disabled={submitting} className="btn-primary py-2.5 mt-2">
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="text-sm text-[var(--color-ink-soft)] mt-6 text-center">
        Already have an account?{' '}
        <Link to="/login" className="text-[var(--color-indigo)] font-medium">
          Sign in
        </Link>
      </p>
    </div>
  )
}
