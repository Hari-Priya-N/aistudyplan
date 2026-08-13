import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const bottomRef = useRef(null)

  useEffect(() => {
    api
      .chatHistory()
      .then(setMessages)
      .catch(() => setMessages([]))
      .finally(() => setLoadingHistory(false))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: text, citations: [] }])
    setSending(true)
    try {
      const res = await api.sendChatMessage(text)
      setMessages((m) => [...m, res])
    } catch {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: "I couldn't reach the tutor just now — please try again.", citations: [] },
      ])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 flex flex-col h-[calc(100vh-4rem)]">
      <h1 className="text-2xl font-semibold mb-1">Tutor chat</h1>
      <p className="text-[var(--color-ink-soft)] mb-4 text-sm">
        Ask about anything in your uploaded material — answers are grounded in your course content.
      </p>

      <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-1">
        {loadingHistory && <p className="text-sm text-[var(--color-ink-soft)]">Loading conversation…</p>}
        {!loadingHistory && messages.length === 0 && (
          <div className="card p-6 text-center text-[var(--color-ink-soft)] text-sm">
            No messages yet — ask a question about a topic you've uploaded.
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
                <div className="mt-2 pt-2 border-t border-white/20 flex flex-wrap gap-1">
                  {m.citations.map((c, ci) => (
                    <span key={ci} className="text-xs font-[var(--font-mono)] bg-[var(--color-gold-tint)] text-[var(--color-gold)] px-1.5 py-0.5 rounded">
                      [{ci + 1}] {typeof c === 'string' ? c : c.source || 'source'}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="card px-4 py-2.5 text-sm text-[var(--color-ink-soft)]">Thinking…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={send} className="flex gap-2 mt-4">
        <input
          className="input-field flex-1"
          placeholder="Ask about a topic…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" disabled={!input.trim() || sending} className="btn-primary px-5">
          Send
        </button>
      </form>
    </div>
  )
}
