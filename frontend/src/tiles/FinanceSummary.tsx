import { useEffect, useMemo, useState } from 'react'
import { getJson } from '../lib/api'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

type SeriesRow = {
  year: number
  revenue: number
  cogs: number
  overheads: number
  ebit: number
  net_profit: number
}

type MarginRow = { year: number; gm_pct: number; op_pct: number; np_pct: number }
type YoYRow = { year: number; revenue_yoy: number | null; cogs_yoy: number | null; overheads_yoy: number | null; net_profit_yoy: number | null; ebit_yoy?: number | null }

type ApiResponse = {
  success: boolean
  years: number[]
  series: SeriesRow[]
  margins: MarginRow[]
  yoy: YoYRow[]
}

export default function FinanceSummary() {
  const [data, setData] = useState<ApiResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fromYear, setFromYear] = useState<number | null>(null)
  const [toYear, setToYear] = useState<number | null>(null)
  const [yoyMetrics, setYoyMetrics] = useState<string[]>(['revenue_yoy', 'cogs_yoy'])
  const [profitMetric, setProfitMetric] = useState<'net_profit' | 'ebit' | 'revenue'>('net_profit')

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        setError(null)
        const res = await getJson<ApiResponse>(`/dashboard/api/metrics/series/`)
        if (!mounted) return
        setData(res)
        if (res.years?.length) {
          setFromYear(res.years[0])
          setToYear(res.years[res.years.length - 1])
        }
      } catch (e: any) {
        if (!mounted) return
        setError(e?.message || 'Nepodařilo se načíst metriky')
      }
    })()
    return () => { mounted = false }
  }, [])

  const yearOptions = data?.years || []
  const filtered = useMemo(() => {
    if (!data) return null
    const fy = fromYear ?? data.years[0]
    const ty = toYear ?? data.years[data.years.length - 1]
    const inRange = (y: number) => y >= fy && y <= ty
    return {
      series: data.series.filter(r => inRange(r.year)),
      margins: data.margins.filter(r => inRange(r.year)),
      yoy: data.yoy.filter(r => inRange(r.year)),
    }
  }, [data, fromYear, toYear])

  function toggleMetric(key: string) {
    setYoyMetrics((prev) => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key])
  }

  const unauthorized = error?.includes('HTTP 401')

  const controls = (
    <div className="flex flex-wrap items-center gap-3">
      <label className="text-sm text-gray-600">Od roku</label>
      <select className="input" value={fromYear ?? ''} onChange={(e) => setFromYear(Number(e.target.value))} disabled={!yearOptions.length}>
        {yearOptions.map((y) => <option key={y} value={y}>{y}</option>)}
      </select>
      <label className="text-sm text-gray-600">Do roku</label>
      <select className="input" value={toYear ?? ''} onChange={(e) => setToYear(Number(e.target.value))} disabled={!yearOptions.length}>
        {yearOptions.map((y) => <option key={y} value={y}>{y}</option>)}
      </select>
      <span className="mx-2 h-6 w-px bg-gray-200" />
      <label className="text-sm text-gray-600">Příběh zisku</label>
      <select className="input" value={profitMetric} onChange={(e) => setProfitMetric(e.target.value as any)}>
        <option value="net_profit">Čistý zisk</option>
        <option value="ebit">EBIT</option>
        <option value="revenue">Tržby</option>
      </select>
    </div>
  )

  if (unauthorized) {
    return (
      <div className="space-y-3">
        {controls}
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
          Pro zobrazení vlastních metrik se přihlaste.
        </p>
      </div>
    )
  }

  if (!data || !filtered) {
    return (
      <div className="space-y-3">
        {controls}
        <p className="text-sm text-gray-500">Načítám finanční metriky…</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {controls}

      {/* Váš příběh zisku (Net Profit/EBIT/Revenue) */}
      <section>
        <h3 className="text-base font-semibold mb-2">Váš příběh zisku</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={filtered.series} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey={profitMetric}
                name={profitMetric === 'net_profit' ? 'Čistý zisk' : profitMetric === 'ebit' ? 'EBIT' : 'Tržby'}
                stroke="#1f77b4"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Trend ziskovosti (marže %) */}
      <section>
        <h3 className="text-base font-semibold mb-2">Trend ziskovosti</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={filtered.margins} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis unit="%" />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="gm_pct" name="Hrubá marže %" stroke="#e67e22" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="op_pct" name="Provozní marže %" stroke="#2ecc71" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="np_pct" name="Čistá marže %" stroke="#9b59b6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Růst tržeb vs COGS */}
      <section>
        <h3 className="text-base font-semibold mb-2">Růst tržeb vs. růst nákladů na prodané zboží</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={filtered.yoy} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis unit="%" />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey={profitMetric === 'net_profit' ? 'net_profit_yoy' : profitMetric === 'ebit' ? 'ebit_yoy' : 'revenue_yoy'}
                name={profitMetric === 'net_profit' ? 'Čistý zisk YoY %' : profitMetric === 'ebit' ? 'EBIT YoY %' : 'Tržby YoY %'}
                stroke="#16a085"
                strokeWidth={2}
                dot={false}
              />
              <Line type="monotone" dataKey="cogs_yoy" name="COGS YoY %" stroke="#c0392b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Růst tržeb vs provozní náklady */}
      <section>
        <h3 className="text-base font-semibold mb-2">Růst tržeb vs. růst provozních nákladů</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={filtered.yoy} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis unit="%" />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey={profitMetric === 'net_profit' ? 'net_profit_yoy' : profitMetric === 'ebit' ? 'ebit_yoy' : 'revenue_yoy'}
                name={profitMetric === 'net_profit' ? 'Čistý zisk YoY %' : profitMetric === 'ebit' ? 'EBIT YoY %' : 'Tržby YoY %'}
                stroke="#16a085"
                strokeWidth={2}
                dot={false}
              />
              <Line type="monotone" dataKey="overheads_yoy" name="Provozní náklady YoY %" stroke="#d35400" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Meziroční přehled – výběr metrik */}
      <section>
        <h3 className="text-base font-semibold mb-3">Meziroční přehled (výběr metrik)</h3>
        <div className="flex flex-wrap gap-3 mb-2 text-sm">
          {[
            { key: 'revenue_yoy', label: 'Tržby YoY %' },
            { key: 'cogs_yoy', label: 'COGS YoY %' },
            { key: 'overheads_yoy', label: 'Provozní náklady YoY %' },
            { key: 'net_profit_yoy', label: 'Čistý zisk YoY %' },
            { key: 'ebit_yoy', label: 'EBIT YoY %' },
          ].map(m => (
            <label key={m.key} className="inline-flex items-center gap-2">
              <input type="checkbox" checked={yoyMetrics.includes(m.key)} onChange={() => toggleMetric(m.key)} />
              {m.label}
            </label>
          ))}
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={filtered.yoy} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis unit="%" />
              <Tooltip />
              <Legend />
              {yoyMetrics.includes('revenue_yoy') && (
                <Line type="monotone" dataKey="revenue_yoy" name="Tržby YoY %" stroke="#1abc9c" strokeWidth={2} dot={false} />
              )}
              {yoyMetrics.includes('cogs_yoy') && (
                <Line type="monotone" dataKey="cogs_yoy" name="COGS YoY %" stroke="#e74c3c" strokeWidth={2} dot={false} />
              )}
              {yoyMetrics.includes('overheads_yoy') && (
                <Line type="monotone" dataKey="overheads_yoy" name="Provozní náklady YoY %" stroke="#f39c12" strokeWidth={2} dot={false} />
              )}
              {yoyMetrics.includes('net_profit_yoy') && (
                <Line type="monotone" dataKey="net_profit_yoy" name="Čistý zisk YoY %" stroke="#8e44ad" strokeWidth={2} dot={false} />
              )}
              {yoyMetrics.includes('ebit_yoy') && (
                <Line type="monotone" dataKey="ebit_yoy" name="EBIT YoY %" stroke="#2980b9" strokeWidth={2} dot={false} />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  )
}

