import { useEffect, useRef, useState } from 'react'
import { postJson } from '../lib/api'

type Message = { role: 'user' | 'assistant'; content: string }

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const boxRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (open) boxRef.current?.scrollTo({ top: boxRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, open])

  async function send() {
    const text = input.trim()
    if (!text) return
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setLoading(true)
    try {
      const res = await postJson<{ response: string; success?: boolean }>(`/chatbot/api/`, {
        message: text,
        context: 'dashboard'
      })
      const reply = res?.response || '…'
      setMessages((m) => [...m, { role: 'assistant', content: reply }])
    } catch (e: any) {
      setMessages((m) => [...m, { role: 'assistant', content: e?.message || 'Chyba komunikace.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {open && (
        <div className="w-80 sm:w-96 card overflow-hidden">
          <div className="card-header">
            <div>
              <h3 className="text-sm font-semibold">Chatbot</h3>
              <p className="text-xs text-gray-500">Finanční asistent</p>
            </div>
            <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-gray-700">✕</button>
          </div>
          <div className="h-1 bg-gradient-to-r from-primary-600 via-secondary-500 to-accent-500" />
          <div ref={boxRef} className="card-body bg-gray-50 dark:bg-gray-900 max-h-80 overflow-auto space-y-3">
            {messages.length === 0 && (
              <p className="text-xs text-gray-500">Zeptejte se na cokoliv k dashboardu…</p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
                <span className={
                  'inline-block px-3 py-2 rounded-lg text-sm ' +
                  (m.role === 'user' ? 'bg-primary-600 text-white' : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700')
                }>
                  {m.content}
                </span>
              </div>
            ))}
            {loading && <p className="text-xs text-gray-500">Píšu odpověď…</p>}
          </div>
          <div className="p-3 border-t border-gray-100 flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') send() }}
              placeholder="Vaše zpráva"
              className="flex-1 rounded-md border-gray-300 focus:border-primary-500 focus:ring-primary-500 text-sm"
            />
            <button onClick={send} disabled={loading} className="btn-primary">Odeslat</button>
          </div>
        </div>
      )}

      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="rounded-full shadow-lg bg-primary-600 hover:bg-primary-700 text-white w-14 h-14 flex items-center justify-center"
          title="Otevřít chatbota"
        >
          💬
        </button>
      )}
    </div>
  )
}
