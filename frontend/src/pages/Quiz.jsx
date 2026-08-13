import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../lib/api'

export default function Quiz() {
  const { topicId } = useParams()
  const [params] = useSearchParams()
  const topicTitle = params.get('title') || 'this topic'

  const [quiz, setQuiz] = useState(null)
  const [answers, setAnswers] = useState({})
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [remediation, setRemediation] = useState(null)
  const [remediationLoading, setRemediationLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .generateQuiz(topicId)
      .then((res) => !cancelled && setQuiz(res))
      .catch((err) => !cancelled && setError(err instanceof ApiError ? err.message : 'Could not generate a quiz.'))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [topicId])

  const selectAnswer = (qIndex, optIndex) => {
    if (result) return
    setAnswers((a) => ({ ...a, [qIndex]: optIndex }))
  }

  const allAnswered = quiz && quiz.questions.every((_, i) => answers[i] !== undefined)

  const explanationFor = (qIndex) => result?.explanations?.find((e) => e.question_index === qIndex)?.explanation

  const onSubmit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const ordered = quiz.questions.map((_, i) => answers[i])
      const res = await api.submitQuiz(quiz.quiz_id, ordered)
      setResult(res)
      if (res.remediation_triggered) {
        setRemediationLoading(true)
        const rem = await api.requestRemediation(topicId).catch(() => null)
        setRemediation(rem)
        setRemediationLoading(false)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not submit the quiz.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16 text-[var(--color-ink-soft)]">Building your quiz…</div>
  if (error && !quiz) return <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16 text-[var(--color-rust)]">{error}</div>

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <Link to="/" className="text-sm text-[var(--color-indigo)] mb-4 inline-block">← Back to dashboard</Link>
      <h1 className="text-3xl font-semibold mb-1">Quiz: {topicTitle}</h1>
      <p className="text-[var(--color-ink-soft)] mb-8">Answer all questions, then submit to see your mastery score.</p>

      <div className="flex flex-col gap-6">
        {quiz.questions.map((q, qIndex) => {
          const explanation = explanationFor(qIndex)
          const wasWrong = !!explanation
          return (
            <div key={qIndex} className="card p-5">
              <p className="font-medium mb-3">{qIndex + 1}. {q.question}</p>
              <div className="flex flex-col gap-2">
                {q.options.map((opt, optIndex) => {
                  const selected = answers[qIndex] === optIndex
                  return (
                    <button
                      key={optIndex}
                      disabled={!!result}
                      onClick={() => selectAnswer(qIndex, optIndex)}
                      className={`text-left px-4 py-2.5 rounded-md border text-sm transition-colors ${
                        result
                          ? selected
                            ? wasWrong
                              ? 'border-[var(--color-rust)] bg-[var(--color-rust-tint)]'
                              : 'border-[var(--color-forest)] bg-[var(--color-forest-tint)]'
                            : 'border-[var(--color-line)]'
                          : selected
                            ? 'border-[var(--color-indigo)] bg-[var(--color-indigo-tint)]'
                            : 'border-[var(--color-line)] hover:border-[var(--color-indigo-soft)]'
                      }`}
                    >
                      {opt}
                    </button>
                  )
                })}
              </div>

              {result && wasWrong && (
                <p className="text-sm text-[var(--color-ink-soft)] bg-[var(--color-paper)] rounded-md p-3 mt-3">
                  {explanation}
                </p>
              )}
            </div>
          )
        })}
      </div>

      {error && <p className="text-sm text-[var(--color-rust)] mt-4">{error}</p>}

      {!result ? (
        <button onClick={onSubmit} disabled={!allAnswered || submitting} className="btn-primary w-full py-2.5 mt-6">
          {submitting ? 'Submitting…' : 'Submit quiz'}
        </button>
      ) : (
        <div className="card p-6 mt-6">
          <p className="text-lg font-semibold">
            Score: {Math.round(result.score * 100)}% {result.passed ? '— mastered ✓' : '— needs more practice'}
          </p>

          {result.remediation_triggered && (
            <div className="mt-4 pt-4 border-t border-[var(--color-line)]">
              <p className="font-medium text-sm mb-1">Targeted review, just for this topic</p>
              {remediationLoading && <p className="text-sm text-[var(--color-ink-soft)]">Preparing a micro-lesson…</p>}
              {remediation && (
                <>
                  <p className="text-sm text-[var(--color-ink-soft)]">{remediation.explanation}</p>
                  <p className="text-sm mt-2 bg-[var(--color-paper)] rounded-md p-3">{remediation.micro_module}</p>
                </>
              )}
            </div>
          )}

          <Link to="/" className="btn-secondary inline-block mt-4 px-4 py-2 text-sm">Back to dashboard</Link>
        </div>
      )}
    </div>
  )
}
