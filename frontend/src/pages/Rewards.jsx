import { useEffect, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { Loading, PageHeader, timeAgo } from '../components/ui'

const RULE_COPY = [
  ['pre_assessment', 'Take a pre-assessment (self-assess before studying a topic)'],
  ['improvement_per_pct', 'Every 1% you improve over your previous attempt (up to +30 per test)'],
  ['topic_mastered', 'Master a topic (reach 75%)'],
  ['quiz_completed', 'Complete a post-preparation or practice test'],
  ['daily_login', 'Daily check-in'],
  ['streak_bonus', 'Extra per day once you keep a 3-day streak'],
  ['study_kit_opened', 'Open a topic’s study kit for the first time'],
]

const BADGE_ICON = {
  first_step: '🎯', improver: '📈', big_leap: '🚀', topic_master: '🏅', scholar: '🎓', regular: '📅', on_fire: '🔥',
}

// Motivation: why students want to self-assess.
export default function Rewards() {
  const [data, setData] = useState(null)
  const [msg, setMsg] = useState(null)
  const [redeeming, setRedeeming] = useState(false)

  const load = () => api.myRewards().then(setData).catch(() => setMsg('Could not load rewards.'))
  useEffect(() => {
    load()
  }, [])

  const redeem = async () => {
    setRedeeming(true)
    setMsg(null)
    try {
      await api.redeemChat()
      setMsg(`Unlocked ${data.chat_quota.redeem_bonus} extra Elara messages for today.`)
      await load()
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : 'Could not redeem right now.')
    } finally {
      setRedeeming(false)
    }
  }

  if (!data) return <Loading>{msg ?? 'Loading rewards…'}</Loading>
  const q = data.chat_quota

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
      <PageHeader
        title="Rewards"
        subtitle="Self-assess, improve, and keep your streak — points unlock extra Elara help and climb you up the class board."
      />

      <div className="grid md:grid-cols-3 gap-4 mb-8">
        <div className="card p-5 md:col-span-2">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--color-ink-soft)] font-medium">Points balance</p>
              <p className="text-4xl font-semibold font-[var(--font-display)] mt-1">{data.balance}</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase tracking-wide text-[var(--color-ink-soft)] font-medium">Level</p>
              <p className="text-4xl font-semibold font-[var(--font-display)] mt-1 text-[var(--color-indigo)]">{data.level}</p>
            </div>
          </div>
          <div className="mt-4 h-2 rounded-full bg-[var(--color-line)] overflow-hidden">
            <div className="h-full bg-[var(--color-gold)] rounded-full" style={{ width: `${Math.round(data.level_progress * 100)}%` }} />
          </div>
          <p className="text-xs text-[var(--color-ink-soft)] mt-2">
            {data.points_to_next_level} points to level {data.level + 1} · {data.lifetime_earned} earned in total
          </p>
        </div>
        <div className="card p-5 flex flex-col justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--color-ink-soft)] font-medium">Streak</p>
            <p className="text-3xl font-semibold font-[var(--font-display)] mt-1">🔥 {data.streak_days} day{data.streak_days === 1 ? '' : 's'}</p>
          </div>
          <p className="text-sm text-[var(--color-ink-soft)]">
            {data.class_rank?.rank ? `Rank #${data.class_rank.rank} of ${data.class_rank.of} in ${data.class_name}` : 'Not ranked yet'}
          </p>
        </div>
      </div>

      <div className="card p-5 mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="font-medium">Elara messages today</p>
          <p className="text-sm text-[var(--color-ink-soft)]">
            {q.remaining} of {q.limit} left{q.bonus ? ` (includes +${q.bonus} unlocked)` : ''}. Spend {q.redeem_cost} points for {q.redeem_bonus} more.
          </p>
          {msg && <p className="text-sm mt-1 text-[var(--color-indigo)]">{msg}</p>}
        </div>
        <button onClick={redeem} disabled={redeeming || data.balance < q.redeem_cost} className="btn-primary px-4 py-2 text-sm shrink-0">
          {redeeming ? 'Unlocking…' : `Unlock ${q.redeem_bonus} messages · ${q.redeem_cost} pts`}
        </button>
      </div>

      <h2 className="text-xl font-semibold mb-3">Badges</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 mb-8">
        {data.badges.map((b) => (
          <div key={b.id} className={`card p-4 text-center ${b.earned ? '' : 'opacity-40 grayscale'}`} title={b.description}>
            <div className="text-3xl">{BADGE_ICON[b.id] ?? '⭐'}</div>
            <p className="text-sm font-semibold mt-2">{b.name}</p>
            <p className="text-[11px] text-[var(--color-ink-soft)] mt-1 leading-snug">{b.description}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4 mb-8">
        <div>
          <h2 className="text-xl font-semibold mb-3">How to earn</h2>
          <div className="card divide-y divide-[var(--color-line)]">
            {RULE_COPY.map(([key, text]) => (
              <div key={key} className="px-4 py-2.5 flex items-center justify-between gap-3 text-sm">
                <span>{text}</span>
                <span className="font-semibold text-[var(--color-gold)] whitespace-nowrap">+{data.rules[key]}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-3">{data.class_name ? `${data.class_name} leaderboard` : 'Leaderboard'}</h2>
          <div className="card divide-y divide-[var(--color-line)]">
            {data.leaderboard.length === 0 && <p className="p-4 text-sm text-[var(--color-ink-soft)]">No points earned yet.</p>}
            {data.leaderboard.map((r) => (
              <div key={r.user_id} className="px-4 py-2.5 flex items-center gap-3 text-sm">
                <span className="w-6 font-[var(--font-mono)] text-[var(--color-ink-soft)]">{r.rank}</span>
                <span className="flex-1 truncate">{r.name}</span>
                <span className="font-semibold">{r.points}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <h2 className="text-xl font-semibold mb-3">Recent points</h2>
      <div className="card divide-y divide-[var(--color-line)]">
        {data.history.length === 0 && <p className="p-4 text-sm text-[var(--color-ink-soft)]">Take your first pre-assessment to start earning.</p>}
        {data.history.map((h, i) => (
          <div key={i} className="px-4 py-2.5 flex items-center justify-between gap-3 text-sm">
            <span>{h.description}</span>
            <span className="flex items-center gap-3 shrink-0">
              <span className="text-xs text-[var(--color-ink-soft)]">{timeAgo(h.created_at)}</span>
              <span className={`font-semibold ${h.points < 0 ? 'text-[var(--color-rust)]' : 'text-[var(--color-forest)]'}`}>
                {h.points > 0 ? '+' : ''}
                {h.points}
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
