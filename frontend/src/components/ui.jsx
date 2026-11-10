// Small shared building blocks for the dashboards.

export const pct = (v) => (v === null || v === undefined ? '—' : `${Math.round(v * 100)}%`)

export function timeAgo(iso) {
  if (!iso) return 'never'
  const d = new Date(iso.endsWith('Z') ? iso : `${iso}Z`)
  const mins = Math.round((Date.now() - d.getTime()) / 60000)
  if (mins < 2) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs} h ago`
  const days = Math.round(hrs / 24)
  return `${days} day${days === 1 ? '' : 's'} ago`
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
      <div>
        <h1 className="text-3xl font-semibold">{title}</h1>
        {subtitle && <p className="text-[var(--color-ink-soft)] mt-1">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  )
}

export function StatCard({ label, value, hint, tone }) {
  const color =
    tone === 'good' ? 'text-[var(--color-forest)]' : tone === 'bad' ? 'text-[var(--color-rust)]' : 'text-[var(--color-ink)]'
  return (
    <div className="card p-4">
      <p className="text-xs uppercase tracking-wide text-[var(--color-ink-soft)] font-medium">{label}</p>
      <p className={`text-2xl font-semibold mt-1 font-[var(--font-display)] ${color}`}>{value}</p>
      {hint && <p className="text-xs text-[var(--color-ink-soft)] mt-1">{hint}</p>}
    </div>
  )
}

export function Delta({ value }) {
  if (value === null || value === undefined) return <span className="text-[var(--color-ink-soft)]">—</span>
  const n = Math.round(value * 100)
  const tone = n > 0 ? 'badge-mastered' : n < 0 ? 'badge-review' : 'badge-pending'
  return (
    <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full ${tone}`}>
      {n > 0 ? '▲ +' : n < 0 ? '▼ ' : ''}
      {n}%
    </span>
  )
}

// Pre-assessment -> post-preparation -> latest, as three thin bars.
export function ScoreTrio({ pre, post, latest, compact = false }) {
  const rows = [
    ['Pre', pre, 'var(--color-rust)'],
    ['Post', post, 'var(--color-gold)'],
    ['Latest', latest, 'var(--color-forest)'],
  ]
  return (
    <div className={`flex flex-col ${compact ? 'gap-0.5 min-w-[120px]' : 'gap-1.5'}`}>
      {rows.map(([label, v, color]) => (
        <div key={label} className="flex items-center gap-2 text-xs">
          <span className="w-10 text-[var(--color-ink-soft)]">{label}</span>
          <div className="flex-1 h-1.5 rounded-full bg-[var(--color-line)] overflow-hidden">
            <div className="h-full rounded-full" style={{ width: `${Math.round((v ?? 0) * 100)}%`, background: color }} />
          </div>
          <span className="w-9 text-right font-[var(--font-mono)]">{pct(v)}</span>
        </div>
      ))}
    </div>
  )
}

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-[var(--color-line)] mb-6" role="tablist">
      {tabs.map(([id, label]) => (
        <button
          key={id}
          role="tab"
          aria-selected={active === id}
          onClick={() => onChange(id)}
          className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
            active === id
              ? 'border-[var(--color-indigo)] text-[var(--color-indigo)]'
              : 'border-transparent text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

export function Empty({ children }) {
  return <div className="card p-10 text-center text-[var(--color-ink-soft)]">{children}</div>
}

export function Table({ head, children }) {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-[var(--color-ink-soft)] border-b border-[var(--color-line)]">
            {head.map((h) => (
              <th key={h} className="px-4 py-3 font-medium whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-line)]">{children}</tbody>
      </table>
    </div>
  )
}

// Simple vertical bar chart (values >= 0). items: [{label, value}]
export function MiniBars({ items, format = (v) => v, height = 120, color = 'var(--color-indigo)', showValues = false }) {
  const max = Math.max(1, ...items.map((i) => i.value || 0))
  return (
    <div className="flex items-end gap-1.5" style={{ height }}>
      {items.map((it) => (
        <div key={it.label} className="flex-1 flex flex-col items-center justify-end h-full min-w-0 group">
          <span className={`text-[10px] text-[var(--color-ink-soft)] ${showValues ? 'font-semibold' : 'opacity-0 group-hover:opacity-100'}`}>
            {format(it.value)}
          </span>
          <div
            className="w-full rounded-t"
            style={{ height: `${((it.value || 0) / max) * 85}%`, minHeight: it.value ? 3 : 1, background: it.value ? color : 'var(--color-line)' }}
            title={`${it.label}: ${format(it.value)}`}
          />
          <span className="text-[10px] text-[var(--color-ink-soft)] mt-1 truncate w-full text-center">{it.label}</span>
        </div>
      ))}
    </div>
  )
}

export function FocusChips({ areas }) {
  if (!areas?.length) return <span className="text-xs text-[var(--color-ink-soft)]">—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {areas.map((a) => (
        <span key={a.topic_id} className="text-xs px-2 py-0.5 rounded-full badge-review whitespace-nowrap" title={`Latest ${pct(a.latest)}`}>
          {a.topic_title} · {pct(a.latest)}
        </span>
      ))}
    </div>
  )
}

export function Loading({ children = 'Loading…' }) {
  return <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 text-[var(--color-ink-soft)]">{children}</div>
}
