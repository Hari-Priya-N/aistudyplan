import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import {
  Delta, Empty, FocusChips, Loading, MiniBars, PageHeader, ScoreTrio, StatCard, Table, Tabs, pct, timeAgo,
} from '../components/ui'

const TABS = [
  ['overview', 'Overview'],
  ['classes', 'Classes'],
  ['subjects', 'Subjects'],
  ['electives', 'Electives'],
  ['faculty', 'Faculty'],
  ['students', 'Students'],
]

const signedPct = (v) => (v === null || v === undefined ? '—' : `${v >= 0 ? '+' : ''}${Math.round(v * 100)}%`)

function Overview({ goToStudent }) {
  const [data, setData] = useState(null)
  const [students, setStudents] = useState([])
  useEffect(() => {
    api.mgmtOverview().then(setData).catch(() => setData(false))
    api.mgmtStudents().then(setStudents).catch(() => {})
  }, [])
  if (data === null) return <Loading />
  if (data === false) return <Empty>Could not load metrics.</Empty>
  const { counts, scores } = data
  const attention = students
    .filter((s) => s.topics_assessed > 0)
    .sort((a, b) => (a.latest_avg ?? 0) - (b.latest_avg ?? 0))
    .slice(0, 5)
  const dayLabel = (iso) => String(new Date(`${iso}T00:00:00`).getDate())

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-3">
        <StatCard label="Students" value={counts.students} hint={`${counts.classes} classes`} />
        <StatCard label="Active (7 days)" value={counts.active_students_7d} hint={`${counts.students ? Math.round((counts.active_students_7d / counts.students) * 100) : 0}% of students`} />
        <StatCard label="Total logins" value={counts.total_logins} />
        <StatCard label="Faculty" value={counts.faculty} />
        <StatCard label="Core subjects" value={counts.subjects} />
        <StatCard label="Electives" value={counts.electives} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
        <StatCard label="Pre-assessment avg" value={pct(scores.pre_assessment_avg)} hint="before studying" />
        <StatCard label="Post-preparation avg" value={pct(scores.post_preparation_avg)} hint="first test after studying" />
        <StatCard label="Latest avg" value={pct(scores.latest_avg)} hint="most recent attempt" />
        <StatCard label="Avg improvement" value={signedPct(scores.improvement_avg)} hint="latest vs pre-assessment" tone={scores.improvement_avg > 0 ? 'good' : undefined} />
        <StatCard label="Topics mastered" value={scores.mastered_topics} hint={`of ${scores.topics_assessed} assessed`} />
      </div>

      <div className="grid md:grid-cols-2 gap-4 mb-8">
        <div className="card p-5">
          <p className="font-medium">Score journey</p>
          <p className="text-xs text-[var(--color-ink-soft)] mb-4">Average score at each attempt on a topic — pre-assessment, post-preparation, then consecutive tests</p>
          <MiniBars
            items={data.score_journey.map((s) => ({ label: s.label.replace('Attempt ', '#'), value: Math.round((s.average ?? 0) * 100) }))}
            format={(v) => `${v}%`}
            color="var(--color-forest)"
            height={150}
            showValues
          />
        </div>
        <div className="card p-5">
          <p className="font-medium">Daily active students</p>
          <p className="text-xs text-[var(--color-ink-soft)] mb-4">Last 14 days (day of month)</p>
          <MiniBars items={data.daily_active.map((d) => ({ label: dayLabel(d.date), value: d.active_students }))} height={150} />
        </div>
      </div>

      <h2 className="text-xl font-semibold mb-3">Students needing attention</h2>
      {attention.length === 0 ? (
        <Empty>No assessed students yet.</Empty>
      ) : (
        <Table head={['Student', 'Class', 'Latest avg', 'Improvement', 'Focus areas']}>
          {attention.map((s) => (
            <tr key={s.user_id} className="hover:bg-[var(--color-paper)] cursor-pointer" onClick={() => goToStudent(s.user_id)}>
              <td className="px-4 py-3 font-medium">{s.name}</td>
              <td className="px-4 py-3 whitespace-nowrap">{s.class_name}</td>
              <td className="px-4 py-3 font-[var(--font-mono)]">{pct(s.latest_avg)}</td>
              <td className="px-4 py-3"><Delta value={s.improvement_avg} /></td>
              <td className="px-4 py-3"><FocusChips areas={s.focus_areas} /></td>
            </tr>
          ))}
        </Table>
      )}
    </>
  )
}

function Classes() {
  const [rows, setRows] = useState(null)
  useEffect(() => {
    api.mgmtClasses().then(setRows).catch(() => setRows([]))
  }, [])
  if (!rows) return <Loading />
  if (!rows.length) return <Empty>No classes yet — register students with a Class column.</Empty>
  return (
    <Table head={['Class', 'Students', 'Active (7d)', 'Avg logins', 'Pre → Post → Latest', 'Improvement', 'Mastered / assessed']}>
      {rows.map((r) => (
        <tr key={r.class_name}>
          <td className="px-4 py-3 font-semibold">{r.class_name}</td>
          <td className="px-4 py-3">{r.students}</td>
          <td className="px-4 py-3">{r.active_students_7d}</td>
          <td className="px-4 py-3">{r.avg_logins ?? '—'}</td>
          <td className="px-4 py-3 min-w-[220px]"><ScoreTrio pre={r.pre_assessment_avg} post={r.post_preparation_avg} latest={r.latest_avg} compact /></td>
          <td className="px-4 py-3"><Delta value={r.improvement_avg} /></td>
          <td className="px-4 py-3">{r.mastered_topics} / {r.topics_assessed}</td>
        </tr>
      ))}
    </Table>
  )
}

function Subjects({ elective }) {
  const [rows, setRows] = useState(null)
  const [faculty, setFaculty] = useState([])
  const [subjectsMeta, setSubjectsMeta] = useState([])
  const load = () => {
    api.mgmtSubjects(elective).then(setRows).catch(() => setRows([]))
    api.listSubjects().then(setSubjectsMeta).catch(() => {})
  }
  useEffect(() => {
    load()
    api.facultyList().then(setFaculty).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elective])
  const facultyIdFor = (id) => subjectsMeta.find((s) => s.id === id)?.faculty_id ?? ''

  const assign = async (subjectId, facultyId) => {
    await api.updateSubject(subjectId, { faculty_id: facultyId }).catch(() => {})
    load()
  }

  if (!rows) return <Loading />
  if (!rows.length) return <Empty>{elective ? 'No electives yet.' : 'No core subjects yet.'}</Empty>
  return (
    <Table head={[elective ? 'Elective' : 'Subject', 'Faculty', 'Enrolled', 'Pre → Post → Latest', 'Improvement', 'Weakest topics']}>
      {rows.map((r) => (
        <tr key={r.subject_id}>
          <td className="px-4 py-3">
            <p className="font-semibold">{r.name}</p>
            <p className="text-xs font-[var(--font-mono)] text-[var(--color-ink-soft)]">{r.code} · {r.content_items} content items</p>
          </td>
          <td className="px-4 py-3">
            <select className="input-field py-1 text-xs" value={facultyIdFor(r.subject_id)} onChange={(e) => assign(r.subject_id, e.target.value)}>
              <option value="">Unassigned</option>
              {faculty.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </td>
          <td className="px-4 py-3">{r.enrolled}</td>
          <td className="px-4 py-3 min-w-[220px]"><ScoreTrio pre={r.pre_assessment_avg} post={r.post_preparation_avg} latest={r.latest_avg} compact /></td>
          <td className="px-4 py-3"><Delta value={r.improvement_avg} /></td>
          <td className="px-4 py-3 text-xs">
            {r.weakest_topics.length ? r.weakest_topics.map((t) => `${t.topic_title} (${pct(t.latest_avg)})`).join(', ') : '—'}
          </td>
        </tr>
      ))}
    </Table>
  )
}

function Faculty() {
  const [rows, setRows] = useState(null)
  useEffect(() => {
    api.mgmtFaculty().then(setRows).catch(() => setRows([]))
  }, [])
  if (!rows) return <Loading />
  if (!rows.length) return <Empty>No faculty accounts yet.</Empty>
  return (
    <Table head={['Faculty', 'Subjects', 'Students reached', 'Content', 'Last active', 'Pre → Post → Latest', 'Improvement']}>
      {rows.map((r) => (
        <tr key={r.faculty_id}>
          <td className="px-4 py-3">
            <p className="font-semibold">{r.name}</p>
            <p className="text-xs text-[var(--color-ink-soft)]">{r.email}</p>
          </td>
          <td className="px-4 py-3 text-xs">{r.subjects.join(', ') || '—'}</td>
          <td className="px-4 py-3">{r.students_reached}</td>
          <td className="px-4 py-3">{r.content_uploaded}</td>
          <td className="px-4 py-3 text-xs whitespace-nowrap">{timeAgo(r.last_active)}</td>
          <td className="px-4 py-3 min-w-[220px]"><ScoreTrio pre={r.pre_assessment_avg} post={r.post_preparation_avg} latest={r.latest_avg} compact /></td>
          <td className="px-4 py-3"><Delta value={r.improvement_avg} /></td>
        </tr>
      ))}
    </Table>
  )
}

function toCsv(rows) {
  const head = ['Name', 'Email', 'Roll no', 'Class', 'Electives', 'Logins', 'Sessions', 'Minutes', 'Last active',
    'Pre-assessment avg', 'Post-preparation avg', 'Latest avg', 'Improvement', 'Topics assessed', 'Mastered', 'Points', 'Focus areas']
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const p = (v) => (v === null || v === undefined ? '' : Math.round(v * 100))
  const lines = rows.map((r) => [r.name, r.email, r.roll_no, r.class_name, (r.electives || []).join('; '), r.logins, r.sessions,
    r.minutes_on_platform, r.last_active, p(r.pre_assessment_avg), p(r.post_preparation_avg), p(r.latest_avg), p(r.improvement_avg),
    r.topics_assessed, r.mastered_topics, r.points, r.focus_areas.map((f) => f.topic_title).join('; ')].map(esc).join(','))
  return [head.map(esc).join(','), ...lines].join('\n')
}

function Students({ goToStudent }) {
  const [rows, setRows] = useState(null)
  const [classes, setClasses] = useState([])
  const [subjects, setSubjects] = useState([])
  const [className, setClassName] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [q, setQ] = useState('')

  useEffect(() => {
    api.mgmtClasses().then((c) => setClasses(c.map((x) => x.class_name))).catch(() => {})
    api.listSubjects().then(setSubjects).catch(() => {})
  }, [])
  useEffect(() => {
    setRows(null)
    api.mgmtStudents({ class_name: className, subject_id: subjectId }).then(setRows).catch(() => setRows([]))
  }, [className, subjectId])

  const shown = useMemo(
    () => (rows ?? []).filter((r) => `${r.name} ${r.roll_no} ${r.email}`.toLowerCase().includes(q.toLowerCase())),
    [rows, q],
  )

  const exportCsv = () => {
    const blob = new Blob([toCsv(shown)], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'student_metrics.csv'
    a.click()
  }

  return (
    <>
      <div className="flex flex-col md:flex-row gap-3 mb-4">
        <select className="input-field" value={className} onChange={(e) => setClassName(e.target.value)}>
          <option value="">All classes</option>
          {classes.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select className="input-field" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
          <option value="">All subjects & electives</option>
          {subjects.map((s) => <option key={s.id} value={s.id}>{s.code} · {s.name}{s.is_elective ? ' (elective)' : ''}</option>)}
        </select>
        <input className="input-field flex-1" placeholder="Search name or roll no…" value={q} onChange={(e) => setQ(e.target.value)} />
        <button onClick={exportCsv} disabled={!shown.length} className="btn-secondary px-4 py-2 text-sm whitespace-nowrap">Export CSV</button>
      </div>
      {!rows ? (
        <Loading />
      ) : !shown.length ? (
        <Empty>No students match.</Empty>
      ) : (
        <Table head={['Student', 'Class', 'Activity', 'Pre → Post → Latest', 'Improvement', 'Points', 'Focus areas']}>
          {shown.map((s) => (
            <tr key={s.user_id} className="hover:bg-[var(--color-paper)] cursor-pointer" onClick={() => goToStudent(s.user_id)}>
              <td className="px-4 py-3">
                <p className="font-medium">{s.name}</p>
                <p className="text-xs font-[var(--font-mono)] text-[var(--color-ink-soft)]">{s.roll_no}</p>
              </td>
              <td className="px-4 py-3">
                {s.class_name}
                {s.electives?.length > 0 && <p className="text-xs text-[var(--color-ink-soft)]">{s.electives.join(', ')}</p>}
              </td>
              <td className="px-4 py-3 text-xs whitespace-nowrap">
                {s.logins} logins · {s.sessions} sessions
                <br />
                <span className="text-[var(--color-ink-soft)]">{s.minutes_on_platform} min · {timeAgo(s.last_active)}</span>
              </td>
              <td className="px-4 py-3 min-w-[200px]"><ScoreTrio pre={s.pre_assessment_avg} post={s.post_preparation_avg} latest={s.latest_avg} compact /></td>
              <td className="px-4 py-3"><Delta value={s.improvement_avg} /></td>
              <td className="px-4 py-3 font-semibold">{s.points}</td>
              <td className="px-4 py-3"><FocusChips areas={s.focus_areas} /></td>
            </tr>
          ))}
        </Table>
      )}
    </>
  )
}

// Management view: predominantly a metric dashboard at class, subject,
// elective, faculty and student level, focused on score improvement.
export default function ManagementDashboard() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const tab = params.get('tab') || 'overview'
  const goToStudent = (id) => navigate(`/management/students/${id}`)

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      <PageHeader
        title="Management dashboard"
        subtitle="How students are improving — from pre-assessment, through post-preparation, to their latest scores."
      />
      <Tabs tabs={TABS} active={tab} onChange={(t) => setParams({ tab: t })} />
      {tab === 'overview' && <Overview goToStudent={goToStudent} />}
      {tab === 'classes' && <Classes />}
      {tab === 'subjects' && <Subjects elective={false} />}
      {tab === 'electives' && <Subjects elective={true} />}
      {tab === 'faculty' && <Faculty />}
      {tab === 'students' && <Students goToStudent={goToStudent} />}
    </div>
  )
}
