import { NavLink } from 'react-router-dom'
import { useAuth, ROLE_LABEL } from '../context/AuthContext'

const linkClass = ({ isActive }) =>
  `px-3 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors ${
    isActive ? 'bg-[var(--color-indigo-tint)] text-[var(--color-indigo)]' : 'text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]'
  }`

const LINKS = {
  student: [
    ['/', 'My path', true],
    ['/chat', 'Elara'],
    ['/progress', 'My progress'],
    ['/rewards', 'Rewards'],
    ['/upload', 'Upload'],
  ],
  instructor: [
    ['/faculty', 'Dashboard'],
    ['/upload', 'Content'],
    ['/roster', 'Students'],
    ['/chat', 'Elara'],
  ],
  management: [
    ['/management', 'Dashboard'],
    ['/roster', 'Registration'],
    ['/upload', 'Content'],
  ],
}

export default function Nav() {
  const { user, logout } = useAuth()
  const links = user ? LINKS[user.role] ?? LINKS.student : []

  return (
    <header className="border-b border-[var(--color-line)] bg-[var(--color-surface)]/80 backdrop-blur sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <NavLink to="/" className="flex items-center gap-2 shrink-0">
          <svg width="28" height="28" viewBox="0 0 64 64" aria-hidden="true">
            <circle cx="32" cy="32" r="30" fill="#2B3A67" />
            <circle cx="32" cy="20" r="5" fill="#F6EFDC" />
            <circle cx="20" cy="40" r="5" fill="#F6EFDC" />
            <circle cx="44" cy="40" r="5" fill="#F6EFDC" />
            <path d="M32 20 L20 40 L44 40 Z" stroke="#B8912B" strokeWidth="2" fill="none" />
          </svg>
          <span className="font-[var(--font-display)] text-lg font-semibold hidden sm:inline">Pathwise</span>
        </NavLink>

        {user && (
          <nav className="flex items-center gap-1 overflow-x-auto">
            {links.map(([to, label, end]) => (
              <NavLink key={to} to={to} end={!!end} className={linkClass}>
                {label}
                {user.role === 'student' && to === '/upload' && <span aria-hidden="true"> 🔒</span>}
              </NavLink>
            ))}
          </nav>
        )}

        <div className="flex items-center gap-3 shrink-0">
          {user ? (
            <>
              <NavLink to="/account" className="hidden md:flex flex-col items-end leading-tight text-right">
                <span className="text-sm font-medium">{user.full_name || user.email.split('@')[0]}</span>
                <span className="text-xs text-[var(--color-ink-soft)]">
                  {ROLE_LABEL[user.role] ?? user.role}
                  {user.class_name ? ` · ${user.class_name}` : ''}
                </span>
              </NavLink>
              <button onClick={logout} className="btn-secondary text-sm px-3 py-1.5">
                Sign out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="btn-secondary text-sm px-3 py-1.5">Sign in</NavLink>
              <NavLink to="/signup" className="btn-primary text-sm px-3 py-1.5">Get started</NavLink>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
