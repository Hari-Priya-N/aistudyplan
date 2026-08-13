import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import MasteryRing from '../components/MasteryRing'

const STATUS_TONE = {
  mastered: 'badge-mastered',
  needs_remediation: 'badge-review',
  in_progress: 'badge-pending',
}

export default function Progress() {
  const { user } = useAuth()
  const [trends, setTrends] = useState(null)
  const [cohort, setCohort] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (user?.role === 'instructor') {
        const res = await api.progressCohort().catch(() => [])
        if (!cancelled) setCohort(res)
      } else {
        const res = await api.progressTrends().catch(() => null)
        if (!cancelled) setTrends(res)
      }
      if (!cancelled) setLoading(false)
    }
    load()
    return () => {
      cancelled = true
    }
  }, [user])

  if (loading) return <div className="max-w-4xl mx-auto px-4 sm:px-6 py-16 text-[var(--color-ink-soft)]">Loading progress…</div>

  if (user?.role === 'instructor') {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <h1 className="text-3xl font-semibold mb-1">Cohort mastery</h1>
        <p className="text-[var(--color-ink-soft)] mb-8">Per-topic mastery across your students.</p>

        {(!cohort || cohort.length === 0) ? (
          <div className="card p-10 text-center text-[var(--color-ink-soft)]">No student activity yet.</div>
        ) : (
          <div className="card divide-y divide-[var(--color-line)]">
            {cohort.map((row, i) => (
              <div key={i} className="p-4 flex items-center gap-4">
                <MasteryRing score={row.average_mastery ?? 0} size={40} />
                <div className="flex-1">
                  <p className="font-medium">{row.topic_title}</p>
                  {row.student_count !== undefined && (
                    <p className="text-xs text-[var(--color-ink-soft)]">{row.student_count} students</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
      <h1 className="text-3xl font-semibold mb-1">Your progress</h1>
      <p className="text-[var(--color-ink-soft)] mb-8">Mastery by topic, updated after every quiz.</p>

      {!trends || trends.trends.length === 0 ? (
        <div className="card p-10 text-center text-[var(--color-ink-soft)]">
          Take a quiz to start tracking your mastery.
        </div>
      ) : (
        <>
          <div className="card px-6 py-4 mb-6 flex items-center gap-4">
            <MasteryRing score={trends.overall_mastery} size={56} />
            <div>
              <p className="font-medium">Overall mastery</p>
              <p className="text-sm text-[var(--color-ink-soft)]">Weighted across {trends.trends.length} topics</p>
            </div>
          </div>

          <div className="card divide-y divide-[var(--color-line)]">
            {trends.trends.map((t) => (
              <div key={t.topic_id} className="p-4 flex items-center gap-4">
                <MasteryRing score={t.score} size={40} />
                <div className="flex-1">
                  <p className="font-medium">{t.topic_title}</p>
                  <p className="text-xs text-[var(--color-ink-soft)]">{t.attempts} attempt{t.attempts === 1 ? '' : 's'}</p>
                </div>
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_TONE[t.status] ?? 'badge-pending'}`}>
                  {t.status.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
