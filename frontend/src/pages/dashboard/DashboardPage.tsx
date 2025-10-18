import { useEffect, useMemo, useState } from 'react'
import { getJson } from '../../lib/api'
import Card from '../../components/ui/Card'
import ProfitStory, { ProfitSeriesRow } from '../../tiles/finance/ProfitStory'
import ProfitabilityTrend, { MarginRow } from '../../tiles/finance/ProfitabilityTrend'
import RevenueVsCOGS, { GrowthRow } from '../../tiles/finance/RevenueVsCOGS'
import RevenueVsOverheads from '../../tiles/finance/RevenueVsOverheads'
import AllMetricsTable, { DashboardRow } from '../../tiles/finance/AllMetricsTable'
import CashflowComparison from '../../tiles/finance/CashflowComparison'

type MetricsResponse = {
  success: boolean
  years: number[]
  series: ProfitSeriesRow[]
  margins: MarginRow[]
  yoy: GrowthRow[]
}

const summaryCards = (rows: DashboardRow[]) => {
  if (!rows.length) {
    return [
      { title: 'Tržby', value: '—', description: 'Žádná data' },
      { title: 'Náklady', value: '—', description: 'Žádná data' },
      { title: 'EBIT', value: '—', description: 'Žádná data' },
      { title: 'Čistý zisk', value: '—', description: 'Žádná data' },
    ]
  }

  const latest = rows.at(-1)!
  return [
    { title: 'Tržby', value: `${latest.revenue.toLocaleString('cs-CZ')} Kč`, description: `Růst ${latest.growth.revenue.toFixed(1)} %` },
    { title: 'Náklady na zboží', value: `${latest.cogs.toLocaleString('cs-CZ')} Kč`, description: `Růst ${latest.growth.cogs.toFixed(1)} %` },
    { title: 'EBIT', value: `${latest.ebit.toLocaleString('cs-CZ')} Kč`, description: `Marže ${latest.profitability.op_pct.toFixed(1)} %` },
    { title: 'Čistý zisk', value: `${latest.net_profit.toLocaleString('cs-CZ')} Kč`, description: `Marže ${latest.profitability.np_pct.toFixed(1)} %` },
  ]
}

/**
 * React stránka pro templates/dashboard/index.html.
 */
export default function DashboardPage() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [rows, setRows] = useState<DashboardRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)

    getJson<MetricsResponse>('/dashboard/api/metrics/series/')
      .then((res) => {
        if (!mounted) return
        setMetrics(res)

        const mergedRows: DashboardRow[] = res.series.map((row) => {
          const yoy = res.yoy.find((y) => y.year === row.year)
          const margin = res.margins.find((m) => m.year === row.year)
          return {
            year: row.year,
            revenue: row.revenue,
            cogs: row.cogs,
            gross_margin: row.revenue - row.cogs,
            overheads: row.overheads,
            ebit: row.ebit,
            net_profit: row.net_profit,
            profitability: {
              gm_pct: margin?.gm_pct ?? 0,
              op_pct: margin?.op_pct ?? 0,
              np_pct: margin?.np_pct ?? 0,
            },
            growth: {
              revenue: yoy?.revenue_yoy ?? 0,
              cogs: yoy?.cogs_yoy ?? 0,
              overheads: yoy?.overheads_yoy ?? 0,
            },
          }
        })
        setRows(mergedRows)
      })
      .catch((e: any) => {
        if (!mounted) return
        setError(e?.message || 'Nepodařilo se načíst data dashboardu.')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  const summary = useMemo(() => summaryCards(rows), [rows])

  if (loading && !metrics) {
    return <p className="text-sm text-slate-500">Načítám data dashboardu…</p>
  }

  if (error && !metrics) {
    return <p className="text-sm text-red-600">{error}</p>
  }

  const years = metrics?.years ?? []

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summary.map((card) => (
          <Card key={card.title} title={card.title} subtitle={card.description}>
            <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">{card.value}</p>
          </Card>
        ))}
      </div>

      {metrics && (
        <>
          <Card title="Váš příběh zisku" subtitle="Vývoj čistého zisku, EBIT a tržeb v čase.">
            <ProfitStory series={metrics.series} years={years} />
          </Card>

          <Card title="Trend ziskovosti" subtitle="Hrubá, provozní a čistá marže v %">
            <ProfitabilityTrend margins={metrics.margins} years={years} />
          </Card>

          <Card title="Růst tržeb vs. náklady na prodané zboží" subtitle="Meziroční růsty">
            <RevenueVsCOGS data={metrics.yoy} years={years} />
          </Card>

          <Card title="Růst tržeb vs. provozní náklady" subtitle="Meziroční růsty">
            <RevenueVsOverheads data={metrics.yoy} years={years} />
          </Card>

          <Card title="Meziroční přehled" subtitle="Detailní tabulka hlavních ukazatelů">
            <AllMetricsTable rows={rows} />
          </Card>

          <CashflowComparison years={years} selectedYear={years.at(-1)} />
        </>
      )}
    </div>
  )
}
