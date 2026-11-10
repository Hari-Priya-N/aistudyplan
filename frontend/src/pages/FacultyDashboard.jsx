import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import { Delta, Empty, FocusChips, Loading, PageHeader, ScoreTrio, Table, pct, timeAgo } from '../components/ui'

// Faculty view: their subjects + LIMITED metrics for each student in them.
export default function FacultyDashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [subjects, setSubjects] = useState(null)
  const [students, setStudents] = useState(null)
  const [subjectId, setSubjectId] = useState('')
  const [sort, setSort] = useState('improvement')

  useEffect(() => {
    api.facultySubjects().then(setSubjects).catch(() => setSubjects([]))
  }, [])
  useEffect(() => {
    setStudents(null)
    api.facultyStudents(subjectId || undefined).then(setStudents).catch(() => setStudents([]))
  }, [subjectId])

  if (!subjects) return <Loading />

  const sorted = [...(students ?? [])].sort((a, b) => {
    if (sort === 'name') return a.name.localeCompare(b.name)
    if (sort === 'activity') return (b.logins ?? 0) - (a.logins ?? 0)
    // students with no tests yet go last for score-based sorts
    const key = sort === 'latest' ? 'latest_avg' : 'improvement_avg'
    if (a[key] === null && b[key] !== null) return 1
    if (b[key] === null && a[key] !== null) return -1
    if (sort === 'latest') return (a.latest_avg ?? -1) - (b.latest_avg ?? -1)
    if (sort === 'activity') return (b.logins ?? 0) - (a.logins ?? 0)
    return (a.improvement_avg ?? -1) - (b.improvement_avg ?? -1) // least improved first
  })

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      <PageHeader
        title={`Hello, ${user?.full_name || 'Faculty'}`}
        subtitle="Your subjects and how each student is progressing in them."
      >
        <Link to="/upload" className="btn-primary px-4 py-2 text-sm">Add content</Link>
        <Link to="/roster" className="btn-secondary px-4 py-2 text-sm">Register students</Link>
      </PageHeader>

      {subjects.length === 0 ? (
        <Empty>
          No subjects assigned to you yet. <Link to="/upload" className="text-[var(--color-indigo)] font-medium">Create a subject and upload content</Link> to get started.
        </Empty>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
          {subjects.map((s) => (
            <button
              key={s.subject_id}
              onClick={() => setSubjectId(subjectId === s.subject_id ? '' : s.subject_id)}
              className={`card p-5 text-left transition-colors ${subjectId === s.subject_id ? 'border-[var(--color-indigo)] ring-2 ring-[var(--color-indigo-tint)]' : 'hover:border-[var(--color-indigo-soft)]'}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-xs font-[var(--font-mono)] text-[var(--color-ink-soft)]">{s.code}{s.is_elective ? ' · elective' : ''}</p>
                  <p className="font-semibold">{s.name}</p>
                </div>
                <Delta value={s.improvement_avg} />
              </div>
              <p className="text-xs text-[var(--color-ink-soft)] mt-1 mb-3">
                {s.enrolled} students · {s.content_items} content items · {s.quiz_attempts} tests taken
              </p>
              <ScoreTrio pre={s.pre_assessment_avg} post={s.post_preparation_avg} latest={s.latest_avg} />
              {s.weakest_topics.length > 0 && (
                <p className="text-xs text-[var(--color-ink-soft)] mt-3">
                  Weakest: {s.weakest_topics.map((t) => `${t.topic_title} (${pct(t.latest_avg)})`).join(', ')}
                </p>
              )}
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <h2 className="text-xl font-semibold">
          Students{subjectId ? ` · ${subjects.find((s) => s.subject_id === subjectId)?.name}` : ''}
        </h2>
        <label className="text-sm flex items-center gap-2">
          Sort by
          <select className="input-field py-1.5" value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="improvement">Least improved first</option>
            <option value="latest">Lowest latest score first</option>
            <option value="activity">Most active first</option>
            <option value="name">Name</option>
          </select>
        </label>
      </div>
      {!students ? (
        <Loading />
      ) : students.length === 0 ? (
        <Empty>No students enrolled in your subjects yet — register them from an Excel sheet.</Empty>
      ) : (
        <Table head={['Student', 'Class', 'Logins', 'Last active', 'Scores', 'Improvement', 'Focus areas']}>
          {sorted.map((s) => (
            <tr key={s.user_id} className="hover:bg-[var(--color-paper)] cursor-pointer" onClick={() => navigate(`/faculty/students/${s.user_id}`)}>
              <td className="px-4 py-3">
                <p className="font-medium">{s.name}</p>
                <p className="text-xs text-[var(--color-ink-soft)] font-[var(--font-mono)]">{s.roll_no ?? s.email}</p>
              </td>
              <td className="px-4 py-3 whitespace-nowrap">{s.class_name ?? '—'}</td>
              <td className="px-4 py-3">{s.logins}</td>
              <td className="px-4 py-3 whitespace-nowrap text-xs">{timeAgo(s.last_active)}</td>
              <td className="px-4 py-3"><ScoreTrio pre={s.pre_assessment_avg} post={s.post_preparation_avg} latest={s.latest_avg} compact /></td>
              <td className="px-4 py-3"><Delta value={s.improvement_avg} /></td>
              <td className="px-4 py-3"><FocusChips areas={s.focus_areas} /></td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  )
}
