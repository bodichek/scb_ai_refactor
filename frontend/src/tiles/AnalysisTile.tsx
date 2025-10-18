import { useState } from 'react'
import { postForm } from '../lib/api'

export default function AnalysisTile() {
  const [notes, setNotes] = useState('')
  const [clientId, setClientId] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <input
          placeholder="Client ID"
          value={clientId}
          onChange={(e) => setClientId(e.target.value)}
          className="w-40 input"
        />
        <span className="text-xs text-gray-500">
          Pro propojení s /coaching/client/&lt;id&gt;/notes/
        </span>
      </div>

      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Poznámky k analýze..."
        className="w-full min-h-[140px] resize-y input"
      />

      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">{notes.length} znaků</span>
        <button
          disabled={!clientId || saving}
          onClick={async () => {
            if (!clientId) return
            setSaving(true)
            setMessage(null)
            try {
              const form = new FormData()
              form.append('notes', notes)
              await postForm(`/coaching/client/${clientId}/notes/`, form)
              setMessage('Poznámky uloženy.')
            } catch (e: any) {
              setMessage(e?.message || 'Chyba ukládání')
            } finally {
              setSaving(false)
            }
          }}
          className="btn-secondary"
        >
          {saving ? 'Ukládám...' : 'Uložit poznámky'}
        </button>
      </div>

      {message && <p className="text-sm text-gray-600">{message}</p>}
    </div>
  )
}
