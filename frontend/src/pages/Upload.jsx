import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api, ApiError } from '../lib/api'
import { PageHeader, timeAgo } from '../components/ui'

const STATUS_COPY = {
  processing: { label: 'Building topics…', tone: 'badge-pending' },
  ready: { label: 'Ready', tone: 'badge-mastered' },
  failed: { label: 'Failed', tone: 'badge-review' },
}

// Students: upload is shown but greyed out (not enabled yet).
function StudentUploadLocked() {
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-3xl font-semibold mb-2">Upload your own material</h1>
      <div className="card p-4 mb-6 bg-[var(--color-indigo-tint)] border-[var(--color-indigo-soft)] text-sm">
        🔒 Coming soon. For now your faculty adds the course content for your subjects — it shows up on your path automatically.
      </div>
      <div aria-disabled="true" className="opacity-45 grayscale pointer-events-none select-none">
        <div className="card p-10 flex flex-col items-center gap-4 text-center">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-indigo)" strokeWidth="1.5">
            <path d="M12 16V4M12 4l-4 4M12 4l4 4" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <p className="font-medium">Drag your notes here, or</p>
          <span className="btn-secondary inline-block px-4 py-2">Browse files</span>
        </div>
        <button disabled className="btn-primary w-full py-2.5 mt-6">Upload</button>
      </div>
    </div>
  )
}

function ContentManager({ isManagement }) {
  const [subjects, setSubjects] = useState([])
  const [subjectId, setSubjectId] = useState('')
  const [mode, setMode] = useState('file')
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [notes, setNotes] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [docs, setDocs] = useState([])
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [newSubject, setNewSubject] = useState(null) // {code, name, is_elective}
  const pollRef = useRef(null)

  const loadDocs = useCallback(() => api.listSyllabi().then(setDocs).catch(() => {}), [])
  const loadSubjects = useCallback(
    () =>
      api.listSubjects().then((s) => {
        setSubjects(s)
        setSubjectId((cur) => cur || s[0]?.id || '')
      }),
    [],
  )

  useEffect(() => {
    loadSubjects()
    loadDocs()
    return () => clearInterval(pollRef.current)
  }, [loadDocs, loadSubjects])

  // Poll while anything is still processing.
  useEffect(() => {
    clearInterval(pollRef.current)
    if (docs.some((d) => d.status === 'processing')) {
      pollRef.current = setInterval(loadDocs, 2000)
    }
    return () => clearInterval(pollRef.current)
  }, [docs, loadDocs])

  const submit = async () => {
    setError(null)
    setBusy(true)
    try {
      if (mode === 'file') {
        await api.uploadSyllabus(file, subjectId)
        setFile(null)
      } else {
        await api.addTextContent(subjectId, title, notes)
        setTitle('')
        setNotes('')
      }
      await loadDocs()
      await loadSubjects()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed. Try again.')
    } finally {
      setBusy(false)
    }
  }

  const createSubject = async () => {
    setError(null)
    try {
      const s = await api.createSubject(newSubject)
      setNewSubject(null)
      await loadSubjects()
      setSubjectId(s.id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create subject')
    }
  }

  const remove = async (id) => {
    if (!window.confirm('Delete this content? Students will no longer see its topics, and scores on those topics are removed.')) return
    await api.deleteSyllabus(id).catch(() => {})
    loadDocs()
  }

  const canSubmit = subjectId && !busy && (mode === 'file' ? !!file : title.trim() && notes.trim().length >= 40)
  const selected = subjects.find((s) => s.id === subjectId)

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
      <PageHeader
        title="Course content"
        subtitle="Upload a syllabus or notes (PDF, JSON, TXT) — or type them in. Topics are extracted automatically and every student enrolled in the subject sees them."
      />

      <div className="card p-6 mb-8 flex flex-col gap-5">
        <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
          <label className="flex flex-col gap-1.5 text-sm font-medium flex-1">
            Subject
            <select className="input-field" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
              {subjects.length === 0 && <option value="">No subjects yet — create one</option>}
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} · {s.name}
                  {s.is_elective ? ' (elective)' : ''}
                  {!s.faculty_id ? ' — unassigned' : ''} · {s.enrolled} students
                </option>
              ))}
            </select>
          </label>
          <button className="btn-secondary px-4 py-2.5 text-sm" onClick={() => setNewSubject({ code: '', name: '', is_elective: false })}>
            + New subject
          </button>
        </div>
        {selected && !selected.faculty_id && !isManagement && (
          <p className="text-xs text-[var(--color-ink-soft)] -mt-3">This subject has no faculty yet — uploading content assigns it to you.</p>
        )}

        {newSubject && (
          <div className="rounded-lg border border-[var(--color-line)] p-4 flex flex-col sm:flex-row gap-3 sm:items-end bg-[var(--color-paper)]">
            <label className="flex flex-col gap-1 text-xs font-medium">
              Code
              <input className="input-field w-28" value={newSubject.code} placeholder="CS201" onChange={(e) => setNewSubject({ ...newSubject, code: e.target.value })} />
            </label>
            <label className="flex flex-col gap-1 text-xs font-medium flex-1">
              Name
              <input className="input-field" value={newSubject.name} placeholder="Data Structures" onChange={(e) => setNewSubject({ ...newSubject, name: e.target.value })} />
            </label>
            <label className="flex items-center gap-2 text-sm pb-2.5">
              <input type="checkbox" checked={newSubject.is_elective} onChange={(e) => setNewSubject({ ...newSubject, is_elective: e.target.checked })} />
              Elective
            </label>
            <div className="flex gap-2">
              <button className="btn-primary px-4 py-2 text-sm" disabled={!newSubject.code || !newSubject.name} onClick={createSubject}>Create</button>
              <button className="btn-secondary px-3 py-2 text-sm" onClick={() => setNewSubject(null)}>Cancel</button>
            </div>
          </div>
        )}

        <div className="flex gap-2">
          {[['file', 'Upload a file'], ['text', 'Type / paste notes']].map(([id, label]) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className={`px-3 py-1.5 rounded-md border text-sm ${mode === id ? 'border-[var(--color-indigo)] bg-[var(--color-indigo-tint)] text-[var(--color-indigo)] font-semibold' : 'border-[var(--color-line)] text-[var(--color-ink-soft)]'}`}
            >
              {label}
            </button>
          ))}
        </div>

        {mode === 'file' ? (
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0])
            }}
            className={`rounded-lg border-2 border-dashed p-8 flex flex-col items-center gap-3 text-center transition-colors ${
              dragOver ? 'border-[var(--color-indigo)] bg-[var(--color-indigo-tint)]' : 'border-[var(--color-line)]'
            }`}
          >
            <p className="font-medium text-sm">Drag a file here, or</p>
            <label className="btn-secondary inline-block px-4 py-2 cursor-pointer text-sm">
              Browse files
              <input type="file" accept=".pdf,.json,.txt,.md" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </label>
            {file && <p className="text-sm font-[var(--font-mono)] text-[var(--color-ink-soft)]">{file.name}</p>}
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <input className="input-field" placeholder="Title, e.g. Unit 3 — Heaps and Priority Queues" value={title} onChange={(e) => setTitle(e.target.value)} />
            <textarea className="input-field min-h-40" placeholder="Paste or type the notes / syllabus content…" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        )}

        {error && <p className="text-sm text-[var(--color-rust)]">{error}</p>}
        <button onClick={submit} disabled={!canSubmit} className="btn-primary w-full py-2.5">
          {busy ? 'Uploading…' : 'Add to subject'}
        </button>
      </div>

      <h2 className="text-xl font-semibold mb-3">{isManagement ? 'All uploaded content' : 'Your uploaded content'}</h2>
      {docs.length === 0 ? (
        <div className="card p-8 text-center text-[var(--color-ink-soft)]">Nothing uploaded yet.</div>
      ) : (
        <div className="card divide-y divide-[var(--color-line)]">
          {docs.map((d) => (
            <div key={d.id} className="px-4 py-3 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{d.filename}</p>
                <p className="text-xs text-[var(--color-ink-soft)]">
                  {d.subject ?? 'No subject'} · {d.topics} topics · {timeAgo(d.uploaded_at)}
                </p>
              </div>
              <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_COPY[d.status]?.tone ?? 'badge-pending'}`}>
                {STATUS_COPY[d.status]?.label ?? d.status}
              </span>
              <button onClick={() => remove(d.id)} className="text-xs text-[var(--color-rust)] hover:underline">Delete</button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Upload() {
  const { user } = useAuth()
  const [config, setConfig] = useState(null)
  useEffect(() => {
    api.publicConfig().then(setConfig).catch(() => setConfig({}))
  }, [])

  if (user?.role === 'student') {
    if (!config) return null
    if (!config.allow_student_uploads) return <StudentUploadLocked />
  }
  return <ContentManager isManagement={user?.role === 'management'} />
}
