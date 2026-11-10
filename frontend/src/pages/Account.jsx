import { useState } from 'react'
import { useAuth, ROLE_LABEL } from '../context/AuthContext'
import { api, ApiError } from '../lib/api'

export default function Account() {
  const { user, refreshUser } = useAuth()
  const [form, setForm] = useState({ current: '', next: '', confirm: '' })
  const [msg, setMsg] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setMsg(null)
    setError(null)
    if (form.next !== form.confirm) return setError('New passwords do not match')
    setBusy(true)
    try {
      await api.changePassword(form.current, form.next)
      setMsg('Password updated.')
      setForm({ current: '', next: '', confirm: '' })
      refreshUser()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not change password')
    } finally {
      setBusy(false)
    }
  }

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  return (
    <div className="max-w-md mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-3xl font-semibold mb-6">Account</h1>
      <div className="card p-5 mb-6 text-sm grid grid-cols-[110px_1fr] gap-y-2">
        <span className="text-[var(--color-ink-soft)]">Name</span><span>{user.full_name || '—'}</span>
        <span className="text-[var(--color-ink-soft)]">Email</span><span>{user.email}</span>
        <span className="text-[var(--color-ink-soft)]">Role</span><span>{ROLE_LABEL[user.role]}</span>
        {user.roll_no && (<><span className="text-[var(--color-ink-soft)]">Roll no</span><span>{user.roll_no}</span></>)}
        {user.class_name && (<><span className="text-[var(--color-ink-soft)]">Class</span><span>{user.class_name}</span></>)}
      </div>
      <form onSubmit={submit} className="card p-6 flex flex-col gap-4">
        <h2 className="font-semibold">Change password</h2>
        {user.must_change_password && (
          <p className="text-sm text-[var(--color-ink-soft)]">Your first password was your roll number — choose a private one.</p>
        )}
        <input type="password" required className="input-field" placeholder="Current password" value={form.current} onChange={set('current')} />
        <input type="password" required minLength={8} className="input-field" placeholder="New password (8+ characters)" value={form.next} onChange={set('next')} />
        <input type="password" required minLength={8} className="input-field" placeholder="Repeat new password" value={form.confirm} onChange={set('confirm')} />
        {error && <p className="text-sm text-[var(--color-rust)]">{error}</p>}
        {msg && <p className="text-sm text-[var(--color-forest)]">{msg}</p>}
        <button disabled={busy} className="btn-primary py-2.5">{busy ? 'Saving…' : 'Update password'}</button>
      </form>
    </div>
  )
}
