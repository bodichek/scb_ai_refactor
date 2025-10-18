import { useMemo, useState } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'

export type GrowthRow = {
  year: number
  revenue_yoy: number | null
  cogs_yoy: number | null
  ebit_yoy?: number | null
  net_profit_yoy?: number | null
}

type Props = {
  data: GrowthRow[]
  years: number[]
}

/**
 * React verze šablony dashboard/index.html (sekce "Růst tržeb vs. růst nákladů na prodané zboží").
 */
export default function RevenueVsCOGS({ data, years }: Props) {
  const [story, setStory] = useState<'revenue_yoy' | 'ebit_yoy' | 'net_profit_yoy'>('revenue_yoy')
  const [range, setRange] = useState<{ from: number | null; to: number | null }>({
    from: years[0] ?? null,
    to: years[years.length - 1] ?? null,
  })

  const filtered = useMemo(() => {
    if (!data.length) return data
    const from = range.from ?? years[0]
    const to = range.to ?? years[years.length - 1]
    return data.filter((row) => row.year >= from && row.year <= to)
  }, [data, years, range])

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
        <select className="input" value={story} onChange={(e) => setStory(e.target.value as any)}>
          <option value="revenue_yoy">Tržby YoY %</option>
          <option value="ebit_yoy">EBIT YoY %</option>
          <option value="net_profit_yoy">Čistý zisk YoY %</option>
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
            <Line
              type="monotone"
              dataKey={story}
              name={
                story === 'revenue_yoy'
                  ? 'Tržby YoY %'
                  : story === 'ebit_yoy'
                  ? 'EBIT YoY %'
                  : 'Čistý zisk YoY %'
              }
              stroke="#0ea5e9"
              strokeWidth={2}
              dot={false}
            />
            <Line type="monotone" dataKey="cogs_yoy" name="COGS YoY %" stroke="#ef4444" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

