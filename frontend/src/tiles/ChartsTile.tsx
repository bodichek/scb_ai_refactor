import { useEffect, useState } from 'react'
import { getJson } from '../lib/api'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'

const fallback = [
  { name: 'Jan', uv: 400, pv: 240 },
  { name: 'Úno', uv: 300, pv: 139 },
  { name: 'Bře', uv: 200, pv: 980 },
  { name: 'Dub', uv: 278, pv: 390 },
  { name: 'Kvě', uv: 189, pv: 480 },
  { name: 'Čer', uv: 239, pv: 380 },
  { name: 'Čvc', uv: 349, pv: 430 },
]

export default function ChartsTile() {
  const [year, setYear] = useState<string>('2025')
  const [html, setHtml] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        setError(null)
        const res = await getJson<{ html?: string; success?: boolean }>(`/dashboard/api/cashflow/${year}/`)
        if (!mounted) return
        if (res && 'html' in res) setHtml(res.html || null)
      } catch (e: any) {
        if (!mounted) return
        setError(e?.message || 'Chyba načtení cashflow')
      }
    })()
    return () => { mounted = false }
  }, [year])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <label className="text-sm text-gray-600">Rok</label>
        <input
          type="number"
          min={2000}
          max={2100}
          value={year}
          onChange={(e) => setYear(e.target.value)}
          className="w-24 input"
        />
      </div>

      {html ? (
        <div className="border rounded-md overflow-auto max-h-72 p-2 bg-white" dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={fallback} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="uv" stroke="#1593e6" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="pv" stroke="#0ea5a3" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}
