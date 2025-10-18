import { useState } from 'react'

type Question = {
  id: string
  label: string
  type: 'text' | 'number' | 'select'
  options?: string[]
}

const sample: Question[] = [
  { id: 'q1', label: 'Jak jste spokojeni?', type: 'select', options: ['Nízká', 'Střední', 'Vysoká'] },
  { id: 'q2', label: 'Počet zaměstnanců', type: 'number' },
  { id: 'q3', label: 'Poznámka', type: 'text' },
]

export default function SurveyTile() {
  const [values, setValues] = useState<Record<string, string>>({})

  function set(id: string, value: string) {
    setValues((v) => ({ ...v, [id]: value }))
  }

  return (
    <form className="space-y-4">
      {sample.map((q) => (
        <div key={q.id} className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">{q.label}</label>
          {q.type === 'select' ? (
            <select
              value={values[q.id] || ''}
              onChange={(e) => set(q.id, e.target.value)}
              className="w-full input"
            >
              <option value="" disabled>Vyberte...</option>
              {q.options!.map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
          ) : (
            <input
              type={q.type}
              value={values[q.id] || ''}
              onChange={(e) => set(q.id, e.target.value)}
              className="w-full input"
            />
          )}
        </div>
      ))}
      <div className="flex justify-end">
        <button type="button" onClick={() => alert(JSON.stringify(values, null, 2))} className="btn-primary">Odeslat</button>
      </div>
    </form>
  )
}
