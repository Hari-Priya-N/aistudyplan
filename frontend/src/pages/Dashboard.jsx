import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import MasteryRing from '../components/MasteryRing'

const STATUS_TONE = {
  mastered: 'badge-mastered',
  needs_remediation: 'badge-review',
  pending: 'badge-pending',
  in_progress: 'badge-pending',
}

export default function Dashboard() {
  const { user } = useAuth()
  const [plan, setPlan] = useState(null)
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [planRes, trendsRes] = await Promise.all([
          api.getStudyPlan().catch(() => []),
          api.progressTrends().catch(() => null),
        ])
        if (!cancelled) {
          setPlan(planRes)
          setTrends(trendsRes)
        }
      } catch (err) {
        if (!cancelled) setError('Could not load your dashboard right now.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const scoreForTopic = (topicId) =>
    trends?.trends?.find((t) => t.topic_id === topicId)?.score ?? 0

  if (loading) {
    return <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 text-[var(--color-ink-soft)]">Loading your path…</div>
  }

  const hasPlan = plan && plan.length > 0

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-semibold">Welcome back, {user?.email?.split('@')[0]}</h1>
          <p className="text-[var(--color-ink-soft)] mt-1">
            {hasPlan ? "Here's what the tutor recommends next." : 'Upload your first syllabus to get a study plan.'}
          </p>
        </div>
        {trends && (
          <div className="card px-5 py-3 flex items-center gap-3">
            <MasteryRing score={trends.overall_mastery} size={48} />
            <div className="text-sm">
              <p className="font-medium">Overall mastery</p>
              <p className="text-[var(--color-ink-soft)]">across all topics</p>
            </div>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-[var(--color-rust)] mb-6">{error}</p>}

      {!hasPlan ? (
        <div className="card p-10 text-center flex flex-col items-center gap-4">
          <p className="text-[var(--color-ink-soft)]">No study plan yet — it's generated automatically once material is uploaded.</p>
          <Link to="/upload" className="btn-primary px-5 py-2.5">Upload course material</Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {plan.map((item) => {
            const score = scoreForTopic(item.topic_id)
            return (
              <div key={item.id} className="card p-5 flex items-center gap-4">
                <span className="font-[var(--font-mono)] text-sm text-[var(--color-ink-soft)] w-6 text-center shrink-0">
                  {item.scheduled_order + 1}
                </span>
                <MasteryRing score={score} size={44} />
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{item.topic_title}</p>
                  <span className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_TONE[item.status] ?? 'badge-pending'}`}>
                    {item.status.replace('_', ' ')}
                  </span>
                  {item.reason && <p className="text-xs text-[var(--color-ink-soft)] mt-1">{item.reason}</p>}
                </div>
                <div className="flex gap-2 shrink-0">
                  <Link to={`/quiz/${item.topic_id}?title=${encodeURIComponent(item.topic_title)}`} className="btn-secondary text-sm px-3 py-1.5">
                    Quiz
                  </Link>
                  <Link to={`/study-kit/${item.topic_id}?title=${encodeURIComponent(item.topic_title)}`} className="btn-secondary text-sm px-3 py-1.5">
                    Study kit
                  </Link>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
