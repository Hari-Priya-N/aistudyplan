import { Delta, MiniBars, PageHeader, StatCard, Table, pct, timeAgo } from './ui'

const EVENT_LABEL = {
  login: 'Signed in',
  session_resumed: 'Came back to study',
  quiz_submitted: 'Submitted a test',
  study_kit_opened: 'Opened a study kit',
  chat_message: 'Asked Elara a question',
}

const KIND_LABEL = { pre_assessment: 'Pre', post_preparation: 'Post', practice: 'Practice' }

// Shared by: student "My progress", faculty (limited) and management student drill-down.
export default function StudentReport({ data, title, subtitle, self = false, actions = null }) {
  const { student, activity, scores, topics, focus_areas, daily_minutes, recent_events } = data
  const dayLabel = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })

  return (
    <div>
      <PageHeader
        title={title ?? student.name}
        subtitle={
          subtitle ??
          [student.roll_no, student.class_name, student.email].filter(Boolean).join(' · ')
        }
      >
        {actions}
      </PageHeader>

      {!self && student.subjects?.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6 -mt-4">
          {student.subjects.map((s) => (
            <span key={s.code} className={`text-xs px-2 py-1 rounded-full ${s.is_elective ? 'bg-[var(--color-gold-tint)] text-[var(--color-gold)]' : 'badge-pending'}`}>
              {s.code} · {s.name}
              {s.is_elective ? ' (elective)' : ''}
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <StatCard label="Logins" value={activity.logins} hint={`Last active ${timeAgo(activity.last_active)}`} />
        <StatCard label="Study sessions" value={activity.sessions} hint={`${activity.minutes_on_platform} min on platform`} />
        <StatCard label="Topics assessed" value={scores.topics_assessed} hint={`${scores.quiz_attempts} tests · ${scores.mastered_topics} mastered`} />
        <StatCard
          label="Avg improvement"
          value={scores.improvement_avg === null ? '—' : `${scores.improvement_avg >= 0 ? '+' : ''}${Math.round(scores.improvement_avg * 100)}%`}
          hint="latest vs pre-assessment"
          tone={scores.improvement_avg > 0 ? 'good' : scores.improvement_avg < 0 ? 'bad' : undefined}
        />
      </div>
      <div className="grid grid-cols-3 gap-3 mb-8">
        <StatCard label="Pre-assessment avg" value={pct(scores.pre_assessment_avg)} />
        <StatCard label="Post-preparation avg" value={pct(scores.post_preparation_avg)} />
        <StatCard label="Latest avg" value={pct(scores.latest_avg)} />
      </div>

      <div className="grid md:grid-cols-5 gap-4 mb-8">
        <div className="card p-5 md:col-span-3">
          <p className="font-medium mb-1">Minutes studied · last 14 days</p>
          <p className="text-xs text-[var(--color-ink-soft)] mb-4">Measured from active sessions</p>
          <MiniBars items={daily_minutes.map((d) => ({ label: dayLabel(d.date), value: d.minutes }))} format={(v) => `${v} min`} />
        </div>
        <div className="card p-5 md:col-span-2">
          <p className="font-medium mb-1">{self ? 'Your focus areas' : 'Focus areas'}</p>
          <p className="text-xs text-[var(--color-ink-soft)] mb-4">Topics still below the 75% mastery mark, weakest first</p>
          {focus_areas.length ? (
            <ul className="flex flex-col gap-2">
              {focus_areas.map((f) => (
                <li key={f.topic_id} className="flex items-center justify-between gap-2 text-sm">
                  <span className="truncate">{f.topic_title}</span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full badge-review">{pct(f.latest)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-[var(--color-ink-soft)]">Nothing flagged — every assessed topic is at mastery. 🎉</p>
          )}
        </div>
      </div>

      <h2 className="text-xl font-semibold mb-3">Score journey by topic</h2>
      {topics.length === 0 ? (
        <div className="card p-8 text-center text-[var(--color-ink-soft)] mb-8">No tests taken yet.</div>
      ) : (
        <div className="mb-8">
          <Table head={['Topic', 'Pre-assessment', 'Post-preparation', 'Consecutive', 'Latest', 'Improvement']}>
            {topics.map((t) => (
              <tr key={t.topic_id}>
                <td className="px-4 py-3">
                  <p className="font-medium">{t.topic_title}</p>
                  <p className="text-xs text-[var(--color-ink-soft)]">{t.subject}</p>
                </td>
                <td className="px-4 py-3 font-[var(--font-mono)]">{pct(t.pre)}</td>
                <td className="px-4 py-3 font-[var(--font-mono)]">{pct(t.post)}</td>
                <td className="px-4 py-3 font-[var(--font-mono)] text-xs">
                  {t.consecutive.length ? t.consecutive.map(pct).join(' → ') : '—'}
                </td>
                <td className="px-4 py-3 font-[var(--font-mono)] font-semibold">{pct(t.latest)}</td>
                <td className="px-4 py-3"><Delta value={t.improvement} /></td>
              </tr>
            ))}
          </Table>
        </div>
      )}

      {recent_events?.length > 0 && (
        <>
          <h2 className="text-xl font-semibold mb-3">Recent activity</h2>
          <div className="card divide-y divide-[var(--color-line)]">
            {recent_events.slice(0, 12).map((e, i) => (
              <div key={i} className="px-4 py-2.5 flex items-center justify-between gap-3 text-sm">
                <span>
                  {EVENT_LABEL[e.event_type] ?? e.event_type.replace(/_/g, ' ')}
                  {e.detail?.kind && <span className="text-[var(--color-ink-soft)]"> · {KIND_LABEL[e.detail.kind] ?? e.detail.kind}</span>}
                  {e.detail?.score !== undefined && <span className="text-[var(--color-ink-soft)]"> · {pct(e.detail.score)}</span>}
                  {e.detail?.topic && <span className="text-[var(--color-ink-soft)]"> · {e.detail.topic}</span>}
                </span>
                <span className="text-xs text-[var(--color-ink-soft)] whitespace-nowrap">{timeAgo(e.created_at)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

