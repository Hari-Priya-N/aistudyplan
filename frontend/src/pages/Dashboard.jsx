import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import MasteryRing from '../components/MasteryRing'
import { Loading } from '../components/ui'

const STATUS_TONE = {
  mastered: 'badge-mastered',
  needs_remediation: 'badge-review',
  pending: 'badge-pending',
  in_progress: 'badge-pending',
}

// Student home: the adaptive study plan for every subject the student is
// enrolled in, plus the motivation strip (points, level, streak, Elara quota).
export default function Dashboard() {
  const { user } = useAuth()
  const [plan, setPlan] = useState(null)
  const [trends, setTrends] = useState(null)
  const [rewards, setRewards] = useState(null)
  const [loading, setLoading] = useState(true)
  const [subjectFilter, setSubjectFilter] = useState('all')

  useEffect(() => {
    let cancelled = false
    async function load() {
      const [planRes, trendsRes, rewardsRes] = await Promise.all([
        api.generateStudyPlan().catch(() => []), // rebuild so newly uploaded faculty content appears
        api.progressTrends().catch(() => null),
        api.myRewards().catch(() => null),
      ])
      if (!cancelled) {
        setPlan(planRes)
        setTrends(trendsRes)
        setRewards(rewardsRes)
        setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const subjects = useMemo(() => [...new Set((plan ?? []).map((p) => p.subject_name))], [plan])
  const scoreForTopic = (topicId) => trends?.trends?.find((t) => t.topic_id === topicId)?.score ?? 0

  if (loading) return <Loading>Loading your path…</Loading>

  const hasPlan = plan && plan.length > 0
  const visible = (plan ?? []).filter((p) => subjectFilter === 'all' || p.subject_name === subjectFilter)
  const pendingPre = (plan ?? []).filter((p) => !p.has_pre_assessment).length

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      {user?.must_change_password && (
        <div className="card p-4 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-[var(--color-gold)] bg-[var(--color-gold-tint)]">
          <p className="text-sm">
            You're using the initial password from registration. Please set your own password.
          </p>
          <Link to="/account" className="btn-primary text-sm px-4 py-2 text-center">Change password</Link>
        </div>
      )}

      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-semibold">Welcome back, {user?.full_name?.split(' ')[0] || user?.email?.split('@')[0]}</h1>
          <p className="text-[var(--color-ink-soft)] mt-1">
            {hasPlan
              ? pendingPre > 0
                ? `${pendingPre} topic${pendingPre === 1 ? '' : 's'} waiting for a quick self-assessment — each one earns you points.`
                : "Here's what Elara recommends next."
              : 'Your study plan appears here once your faculty adds course content.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {trends && (
            <div className="card px-4 py-2.5 flex items-center gap-3">
              <MasteryRing score={trends.overall_mastery} size={44} />
              <div className="text-sm">
                <p className="font-medium">Overall mastery</p>
                <p className="text-[var(--color-ink-soft)] text-xs">across your topics</p>
              </div>
            </div>
          )}
          {rewards && (
            <Link to="/rewards" className="card px-4 py-2.5 flex items-center gap-4 hover:border-[var(--color-indigo-soft)]">
              <div className="text-sm">
                <p className="font-semibold font-[var(--font-display)] text-lg leading-none">{rewards.balance}</p>
                <p className="text-[var(--color-ink-soft)] text-xs mt-1">points · level {rewards.level}</p>
              </div>
              <div className="text-sm">
                <p className="font-semibold font-[var(--font-display)] text-lg leading-none">🔥 {rewards.streak_days}</p>
                <p className="text-[var(--color-ink-soft)] text-xs mt-1">day streak</p>
              </div>
              {rewards.class_rank?.rank && (
                <div className="text-sm">
                  <p className="font-semibold font-[var(--font-display)] text-lg leading-none">#{rewards.class_rank.rank}</p>
                  <p className="text-[var(--color-ink-soft)] text-xs mt-1">in {rewards.class_name || 'class'}</p>
                </div>
              )}
            </Link>
          )}
        </div>
      </div>

      {!hasPlan ? (
        <div className="card p-10 text-center flex flex-col items-center gap-3">
          <p className="text-[var(--color-ink-soft)]">
            No topics yet. Once your faculty uploads material for your subjects, your personalised path appears here.
          </p>
          <Link to="/chat" className="btn-secondary px-5 py-2.5">Say hi to Elara</Link>
        </div>
      ) : (
        <>
          {subjects.length > 1 && (
            <div className="flex flex-wrap gap-2 mb-5">
              {['all', ...subjects].map((s) => (
                <button
                  key={s}
                  onClick={() => setSubjectFilter(s)}
                  className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                    subjectFilter === s
                      ? 'border-[var(--color-indigo)] bg-[var(--color-indigo-tint)] text-[var(--color-indigo)] font-semibold'
                      : 'border-[var(--color-line)] text-[var(--color-ink-soft)]'
                  }`}
                >
                  {s === 'all' ? 'All subjects' : s}
                  {s !== 'all' && plan.find((p) => p.subject_name === s)?.is_elective && ' · elective'}
                </button>
              ))}
            </div>
          )}

          <div className="grid gap-3">
            {visible.map((item) => {
              const score = scoreForTopic(item.topic_id)
              const title = encodeURIComponent(item.topic_title)
              return (
                <div key={item.id} className="card p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center gap-4">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <MasteryRing score={score} size={44} />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{item.topic_title}</p>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <span className="text-xs text-[var(--color-ink-soft)]">{item.subject_name}</span>
                        {item.has_pre_assessment ? (
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_TONE[item.status] ?? 'badge-pending'}`}>
                            {item.status.replace('_', ' ')}
                          </span>
                        ) : (
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-[var(--color-gold-tint)] text-[var(--color-gold)]">
                            not assessed yet
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    {!item.has_pre_assessment ? (
                      <>
                        <Link to={`/quiz/${item.topic_id}?title=${title}`} className="btn-primary text-sm px-3 py-1.5">
                          Start pre-assessment · +10 pts
                        </Link>
                        <span
                          className="btn-secondary text-sm px-3 py-1.5 opacity-50 cursor-not-allowed"
                          title="Unlocks after the pre-assessment"
                        >
                          🔒 Study kit
                        </span>
                      </>
                    ) : (
                      <>
                        <Link to={`/study-kit/${item.topic_id}?title=${title}`} className="btn-secondary text-sm px-3 py-1.5">
                          Study kit
                        </Link>
                        <Link to={`/quiz/${item.topic_id}?title=${title}`} className="btn-primary text-sm px-3 py-1.5">
                          {item.status === 'mastered' ? 'Practice' : 'Take test'}
                        </Link>
                      </>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
