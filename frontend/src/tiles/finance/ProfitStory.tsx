import { useMemo, useState } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'

export type ProfitSeriesRow = {
  year: number
  revenue: number
  overheads: number
  ebit: number
  net_profit: number
}

type ProfitStoryProps = {
  series: ProfitSeriesRow[]
  years: number[]
}

/**
 * React verze šablony templates/dashboard/index.html (sekce „Váš příběh zisku“).
 */
export default function ProfitStory({ series, years }: ProfitStoryProps) {
  const [metric, setMetric] = useState<'net_profit' | 'ebit' | 'revenue'>('net_profit')
  const [range, setRange] = useState<{ from: number | null; to: number | null }>({
    from: years[0] ?? null,
    to: years[years.length - 1] ?? null,
  })

  const filtered = useMemo(() => {
    if (!series.length) return series
    const from = range.from ?? years[0]
    const to = range.to ?? years[years.length - 1]
    return series.filter((row) => row.year >= from && row.year <= to)
  }, [series, years, range])

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
        <span className="mx-2 h-6 w-px bg-slate-200" />
        <label className="text-sm text-slate-600">Příběh zisku</label>
        <select className="input" value={metric} onChange={(e) => setMetric(e.target.value as any)}>
          <option value="net_profit">Čistý zisk</option>
          <option value="ebit">EBIT</option>
          <option value="revenue">Tržby</option>
        </select>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filtered} margin={{ top: 12, right: 20, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="year" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey={metric}
              name={metric === 'net_profit' ? 'Čistý zisk' : metric === 'ebit' ? 'EBIT' : 'Tržby'}
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

