import { useEffect, useMemo, useState } from "react"
import apiClient from "../../lib/apiClient"
import Card from "../../components/ui/Card"
import Table from "../../components/ui/Table"
import LineChartCard from "../../components/charts/LineChartCard"

type ProfitRow = {
  year: number
  revenue: number
  cogs: number
  gross_margin: number
  overheads: number
  ebit: number
  net_profit: number
  gm_pct: number
  op_pct: number
  np_pct: number
}

type ProfitabilityResponse = {
  success: boolean
  rows: ProfitRow[]
}

export default function ProfitabilityPage() {
  const [data, setData] = useState<ProfitRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    apiClient
      .get<ProfitabilityResponse>("/dashboard/api/profitability/")
      .then((res) => {
        if (mounted) setData(res.rows || [])
      })
      .catch((e: any) => {
        if (mounted) setError(e?.message || "Nepodařilo se načíst data ziskovosti.")
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const latest = data.at(-1)

  const chartData = useMemo(
    () =>
      data.map((row) => ({
        year: row.year,
        revenue: row.revenue,
        gross_margin: row.gross_margin,
        net_profit: row.net_profit,
      })),
    [data],
  )

  const tableRows = useMemo(
    () =>
      data.map((row) => [
        row.year,
        row.revenue.toLocaleString("cs-CZ"),
        row.gross_margin.toLocaleString("cs-CZ"),
        row.net_profit.toLocaleString("cs-CZ"),
        `${row.gm_pct.toFixed(1)} %`,
        `${row.op_pct.toFixed(1)} %`,
        `${row.np_pct.toFixed(1)} %`,
      ]),
    [data],
  )

  return (
    <div className="space-y-6">
      <Card title="Přehled ziskovosti" subtitle="Klíčové ukazatele z finančních výkazů.">
        {loading && <p className="text-sm text-slate-500">Načítám data…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Stat label="Tržby" value={latest ? `${latest.revenue.toLocaleString("cs-CZ")} Kč` : "—"} />
            <Stat label="Hrubá marže" value={latest ? `${latest.gross_margin.toLocaleString("cs-CZ")} Kč` : "—"} />
            <Stat label="Čistý zisk" value={latest ? `${latest.net_profit.toLocaleString("cs-CZ")} Kč` : "—"} />
            <Stat label="Čistá marže" value={latest ? `${latest.np_pct.toFixed(1)} %` : "—"} />
          </div>
        )}
      </Card>

      {chartData.length > 0 && (
        <LineChartCard
          title="Vývoj ziskovosti"
          subtitle="Porovnání tržeb, hrubé marže a čistého zisku podle roku."
          data={chartData}
          xKey="year"
          lines={[
            { dataKey: "revenue", name: "Tržby", color: "#2563eb" },
            { dataKey: "gross_margin", name: "Hrubá marže", color: "#10b981" },
            { dataKey: "net_profit", name: "Čistý zisk", color: "#f97316" },
          ]}
        />
      )}

      <Card title="Tabulkový přehled">
        <Table
          headers={["Rok", "Tržby", "Hrubá marže", "Čistý zisk", "Hrubá marže %", "Provozní marže %", "Čistá marže %"]}
          rows={tableRows}
          emptyMessage="Zatím nemáte žádné finanční výkazy."
        />
      </Card>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{value}</p>
    </div>
  )
}
