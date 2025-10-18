import { useMemo, useState } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'

export type MarginRow = { year: number; gm_pct: number; op_pct: number; np_pct: number }

type ProfitabilityTrendProps = {
  margins: MarginRow[]
  years: number[]
}

/**
 * React verze šablony dashboard/index.html (sekce "Trend ziskovosti").
 */
export default function ProfitabilityTrend({ margins, years }: ProfitabilityTrendProps) {
  const [range, setRange] = useState<{ from: number | null; to: number | null }>({
    from: years[0] ?? null,
    to: years[years.length - 1] ?? null,
  })

  const filtered = useMemo(() => {
    if (!margins.length) return margins
    const from = range.from ?? years[0]
    const to = range.to ?? years[years.length - 1]
    return margins.filter((row) => row.year >= from && row.year <= to)
  }, [margins, years, range])

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-slate-600">Od</label>
        <select
          className="input"
          value={range.from ?? ''}
          onChange={(e) => setRange((prev) => ({ ...prev, from: Number(e.target.value) }))}
          disabled={!years.length}
        >
          {years.map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </select>
        <label className="text-sm text-slate-600">Do</label>
        <select
          className="input"
          value={range.to ?? ''}
          onChange={(e) => setRange((prev) => ({ ...prev, to: Number(e.target.value) }))}
          disabled={!years.length}
        >
          {years.map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </select>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filtered} margin={{ top: 12, right: 20, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="year" />
            <YAxis unit="%" />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="gm_pct" name="Hrubá marže %" stroke="#f97316" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="op_pct" name="Provozní marže %" stroke="#22c55e" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="np_pct" name="Čistá marže %" stroke="#a855f7" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
