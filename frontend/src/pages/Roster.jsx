import { useEffect, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { PageHeader, Table } from '../components/ui'

// Faculty / Management: register students in bulk from an Excel sheet
// (email, roll/admission no, class, subjects + electives).
export default function Roster() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [students, setStudents] = useState([])
  const [filter, setFilter] = useState('')

  const load = () => api.rosterStudents().then(setStudents).catch(() => {})
  useEffect(() => {
    load()
  }, [])

  const downloadTemplate = async () => {
    const blob = await api.downloadRosterTemplate()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'student_roster_template.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  }

  const upload = async () => {
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const res = await api.uploadRoster(file)
      setResult(res)
      setFile(null)
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  const shown = students.filter((s) =>
    `${s.name} ${s.email} ${s.roll_no ?? ''} ${s.class_name ?? ''} ${s.subjects.join(' ')}`.toLowerCase().includes(filter.toLowerCase()),
  )

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
      <PageHeader
        title="Student registration"
        subtitle="Upload an Excel sheet with each student's email, roll / admission number, class, subjects and electives."
      >
        <button onClick={downloadTemplate} className="btn-secondary px-4 py-2 text-sm">Download Excel template</button>
      </PageHeader>

      <div className="card p-6 mb-8 flex flex-col gap-4">
        <div className="grid sm:grid-cols-3 gap-3 text-sm">
          <div className="rounded-md bg-[var(--color-paper)] p-3">
            <p className="font-semibold">1 · Fill the template</p>
            <p className="text-[var(--color-ink-soft)] text-xs mt-1">Name, Email, Roll No, Class, Subjects, Electives. Subjects and electives are comma separated codes or names.</p>
          </div>
          <div className="rounded-md bg-[var(--color-paper)] p-3">
            <p className="font-semibold">2 · Upload it here</p>
            <p className="text-[var(--color-ink-soft)] text-xs mt-1">Accounts are created and enrolled. Re-uploading updates students — nothing is duplicated.</p>
          </div>
          <div className="rounded-md bg-[var(--color-paper)] p-3">
            <p className="font-semibold">3 · Students sign in</p>
            <p className="text-[var(--color-ink-soft)] text-xs mt-1">With their email or roll number. First password = roll number; they're asked to change it.</p>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
          <label className="btn-secondary inline-block px-4 py-2 cursor-pointer text-sm text-center">
            Choose .xlsx / .csv
            <input type="file" accept=".xlsx,.csv" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <span className="text-sm font-[var(--font-mono)] text-[var(--color-ink-soft)] flex-1 truncate">{file?.name ?? 'No file chosen'}</span>
          <button onClick={upload} disabled={!file || busy} className="btn-primary px-5 py-2 text-sm">
            {busy ? 'Registering…' : 'Register students'}
          </button>
        </div>
        {error && <p className="text-sm text-[var(--color-rust)]">{error}</p>}

        {result && (
          <div className="rounded-lg border border-[var(--color-line)] p-4 text-sm flex flex-col gap-2">
            <p className="font-semibold">
              {result.students_created} created · {result.students_updated} updated · {result.enrollments_added} enrollments added
              <span className="font-normal text-[var(--color-ink-soft)]"> ({result.rows_read} rows read)</span>
            </p>
            {result.subjects_created.length > 0 && (
              <p className="text-[var(--color-ink-soft)]">New subjects created: {result.subjects_created.join(', ')}</p>
            )}
            {result.errors.length > 0 && (
              <div>
                <p className="font-medium text-[var(--color-rust)]">{result.errors.length} row(s) skipped:</p>
                <ul className="list-disc ml-5 text-[var(--color-ink-soft)]">
                  {result.errors.map((e, i) => (
                    <li key={i}>Row {e.row}: {e.error}</li>
                  ))}
                </ul>
              </div>
            )}
            {result.generated_passwords.length > 0 && (
              <div>
                <p className="font-medium">Generated passwords (share privately — shown once):</p>
                <ul className="font-[var(--font-mono)] text-xs">
                  {result.generated_passwords.map((g) => (
                    <li key={g.email}>{g.email} — {g.password}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-xs text-[var(--color-ink-soft)]">{result.password_rule}</p>
          </div>
        )}
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <h2 className="text-xl font-semibold">Registered students ({students.length})</h2>
        <input className="input-field sm:w-72" placeholder="Search name, roll no, class, subject…" value={filter} onChange={(e) => setFilter(e.target.value)} />
      </div>
      {students.length === 0 ? (
        <div className="card p-8 text-center text-[var(--color-ink-soft)]">No students registered in your subjects yet.</div>
      ) : (
        <Table head={['Name', 'Roll no', 'Class', 'Subjects', 'Signed in']}>
          {shown.map((s) => (
            <tr key={s.id}>
              <td className="px-4 py-2.5">
                <p className="font-medium">{s.name}</p>
                <p className="text-xs text-[var(--color-ink-soft)]">{s.email}</p>
              </td>
              <td className="px-4 py-2.5 font-[var(--font-mono)]">{s.roll_no ?? '—'}</td>
              <td className="px-4 py-2.5">{s.class_name ?? '—'}</td>
              <td className="px-4 py-2.5 text-xs">{s.subjects.join(', ')}</td>
              <td className="px-4 py-2.5">{s.first_login_done ? '✓' : <span className="text-[var(--color-ink-soft)]">not yet</span>}</td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  )
}
