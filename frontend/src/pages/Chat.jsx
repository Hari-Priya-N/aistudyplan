import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../lib/api'

// Elara — the AI tutor chat. Students get a daily message quota that points can extend.
export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [quota, setQuota] = useState(null)
  const [notice, setNotice] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    api
      .chatHistory()
      .then(setMessages)
      .catch(() => setMessages([]))
      .finally(() => setLoadingHistory(false))
    api.chatQuota().then(setQuota).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const outOfMessages = quota?.limited && quota.remaining <= 0

  const send = async (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending || outOfMessages) return
    setInput('')
    setNotice(null)
    setMessages((m) => [...m, { role: 'user', content: text, citations: [] }])
    setSending(true)
    try {
      const res = await api.sendChatMessage(text)
      setMessages((m) => [...m, res])
      if (res.quota) setQuota(res.quota)
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setMessages((m) => m.slice(0, -1))
        setInput(text)
        setNotice(err.message)
        api.chatQuota().then(setQuota).catch(() => {})
      } else {
        setMessages((m) => [
          ...m,
          { role: 'assistant', content: "I couldn't reach Elara just now — please try again.", citations: [] },
        ])
      }
    } finally {
      setSending(false)
    }
  }

  const redeem = async () => {
    try {
      const q = await api.redeemChat()
      setQuota(q)
      setNotice(null)
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : 'Could not redeem points right now.')
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 flex flex-col h-[calc(100vh-4rem)]">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h1 className="text-2xl font-semibold mb-1">Elara</h1>
          <p className="text-[var(--color-ink-soft)] text-sm">
            Your AI tutor — answers are grounded in your subjects' course material.
          </p>
        </div>
        {quota?.limited && (
          <div className="text-right shrink-0">
            <p className="text-sm font-semibold">{quota.remaining} / {quota.limit}</p>
            <p className="text-xs text-[var(--color-ink-soft)]">messages left today</p>
          </div>
        )}
      </div>

      {quota?.limited && (
        <div className="h-1.5 rounded-full bg-[var(--color-line)] overflow-hidden mb-4">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.round((quota.remaining / Math.max(1, quota.limit)) * 100)}%`,
              background: quota.remaining > 3 ? 'var(--color-indigo)' : 'var(--color-rust)',
            }}
          />
        </div>
      )}

      <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-1">
        {loadingHistory && <p className="text-sm text-[var(--color-ink-soft)]">Loading conversation…</p>}
        {!loadingHistory && messages.length === 0 && (
          <div className="card p-6 text-center text-[var(--color-ink-soft)] text-sm">
            Ask Elara about any topic in your subjects — e.g. “What should I study next?” or “Explain BFS vs DFS”.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2.5 text-sm ${
                m.role === 'user' ? 'bg-[var(--color-indigo)] text-white' : 'card'
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.citations?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-[var(--color-line)] flex flex-wrap gap-1">
                  {m.citations.map((c, ci) => (
                    <span
                      key={ci}
                      title={typeof c === 'string' ? c : c.excerpt}
                      className="text-xs font-[var(--font-mono)] bg-[var(--color-gold-tint)] text-[var(--color-gold)] px-1.5 py-0.5 rounded"
                    >
                      [{ci + 1}] source
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="card px-4 py-2.5 text-sm text-[var(--color-ink-soft)]">Elara is thinking…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {(notice || outOfMessages) && (
        <div className="card p-3 mt-3 text-sm flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-[var(--color-rust-tint)] border-[var(--color-rust)]">
          <span>{notice ?? "You've used today's Elara messages."}</span>
          <span className="flex gap-2 shrink-0">
            <button onClick={redeem} className="btn-primary px-3 py-1.5 text-xs">
              Unlock {quota?.redeem_bonus} · {quota?.redeem_cost} pts
            </button>
            <Link to="/rewards" className="btn-secondary px-3 py-1.5 text-xs">Rewards</Link>
          </span>
        </div>
      )}

      <form onSubmit={send} className="flex gap-2 mt-4">
        <input
          className="input-field flex-1"
          placeholder={outOfMessages ? 'Daily limit reached' : 'Ask Elara about a topic…'}
          value={input}
          disabled={outOfMessages}
          maxLength={2000}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" disabled={!input.trim() || sending || outOfMessages} className="btn-primary px-5">
          Send
        </button>
      </form>
    </div>
  )
}
