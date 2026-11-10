import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../lib/api'

export default function StudyKit() {
  const { topicId } = useParams()
  const [params] = useSearchParams()
  const topicTitle = params.get('title') || 'this topic'

  const [kit, setKit] = useState(null)
  const [flipped, setFlipped] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .generateStudyKit(topicId)
      .then((res) => !cancelled && setKit(res))
      .catch((err) => !cancelled && setError(err instanceof ApiError ? err.message : 'Could not build a study kit.'))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [topicId])

  if (loading) return <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-[var(--color-ink-soft)]">Assembling your study kit…</div>
  if (error)
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16">
        <p className="text-[var(--color-rust)] mb-4">{error}</p>
        {error.toLowerCase().includes('pre-assessment') && (
          <Link to={`/quiz/${topicId}?title=${encodeURIComponent(topicTitle)}`} className="btn-primary px-4 py-2 inline-block">
            Take the pre-assessment · +10 pts
          </Link>
        )}
      </div>
    )

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
      <Link to="/" className="text-sm text-[var(--color-indigo)] mb-4 inline-block">← Back to dashboard</Link>
      <h1 className="text-3xl font-semibold mb-1">Study kit: {topicTitle}</h1>
      <p className="text-[var(--color-ink-soft)] mb-8">Summary, flashcards, and a worked example, generated from your material.</p>

      <section className="card p-6 mb-6">
        <h2 className="text-lg font-semibold mb-2">Summary</h2>
        <p className="text-[var(--color-ink-soft)] leading-relaxed">{kit.summary}</p>
      </section>

      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Flashcards</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          {kit.flashcards.map((card, i) => (
            <button
              key={i}
              onClick={() => setFlipped((f) => ({ ...f, [i]: !f[i] }))}
              className="card p-4 text-left h-28 flex items-center justify-center text-center hover:border-[var(--color-indigo-soft)] transition-colors"
            >
              <span className={flipped[i] ? 'text-[var(--color-indigo)] font-medium' : ''}>
                {flipped[i] ? card.back : card.front}
              </span>
            </button>
          ))}
        </div>
        <p className="text-xs text-[var(--color-ink-soft)] mt-2">Tap a card to flip it.</p>
      </section>

      {kit.step_by_step_guide?.length > 0 && (
        <section className="card p-6 mb-6">
          <h2 className="text-lg font-semibold mb-3">Worked example</h2>
          <ol className="flex flex-col gap-2">
            {kit.step_by_step_guide.map((step, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="font-[var(--font-mono)] text-[var(--color-gold)] shrink-0">{String(i + 1).padStart(2, '0')}</span>
                <span className="text-[var(--color-ink-soft)]">{step}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {kit.quiz?.length > 0 && (
        <section className="flex items-center justify-between card p-5">
          <div>
            <p className="font-medium">A quick quiz on this topic is ready</p>
            <p className="text-sm text-[var(--color-ink-soft)]">{kit.quiz.length} questions</p>
          </div>
          <Link to={`/quiz/${topicId}?title=${encodeURIComponent(topicTitle)}`} className="btn-primary text-sm px-4 py-2">
            Take quiz →
          </Link>
        </section>
      )}
    </div>
  )
}
