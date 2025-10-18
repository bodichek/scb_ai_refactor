import { useEffect, useState, type ReactNode } from "react"
import Card from "../../components/ui/Card"
import Table from "../../components/ui/Table"
import apiClient from "../../lib/apiClient"

type CashflowResponse = {
  success: boolean
  years: number[]
  current_year: number | null
  cashflow: CashflowData | null
}

type CashflowData = {
  revenue: number
  cogs: number
  gross_margin: number
  gross_cash_profit: number
  overheads: number
  operating_cash_profit: number
  operating_cash_flow: number
  retained_profit: number
  net_cash_flow: number
  interest: number
  taxation: number
  extraordinary: number
  dividends: number
  depreciation: number
  fixed_assets: number
  other_assets: number
  capital_withdrawn: number
  variance: {
    gross: number
    operating: number
    net: number
  }
}

export default function CashflowPage() {
  const [years, setYears] = useState<number[]>([])
  const [year, setYear] = useState<number | null>(null)
  const [cashflow, setCashflow] = useState<CashflowData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function fetchData(nextYear?: number) {
    setLoading(true)
    setError(null)
    try {
      const query = typeof nextYear === "number" ? `?year=${nextYear}` : ""
      const res = await apiClient.get<CashflowResponse>(`/dashboard/api/cashflow/summary/${query}`)
      setYears(res.years ?? [])
      setYear(res.current_year ?? res.years?.at(-1) ?? null)
      setCashflow(res.cashflow ?? null)
    } catch (e: any) {
      setError(e?.message || "Nepodařilo se načíst data cashflow.")
    } finally {
      setLoading(false)
    }
  }

  function handleYearChange(value: string) {
    const next = Number(value)
    setYear(next)
    fetchData(next)
  }

  const tableRows = cashflow ? buildCashflowRows(cashflow) : []

  return (
    <div className="space-y-6">
      <Card title="Zisk vs. peněžní tok" subtitle="Porovnání účetního pohledu a skutečného cash flow.">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium text-slate-600">Rok:</label>
          <select
            className="input w-32"
            value={year ?? ""}
            onChange={(e) => handleYearChange(e.target.value)}
            disabled={years.length === 0}
          >
            {years.length === 0 ? (
              <option value="" disabled>
                Žádná data
              </option>
            ) : (
              years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))
            )}
          </select>
          {loading && <span className="text-sm text-slate-500">Načítám…</span>}
          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>
      </Card>

      {cashflow ? (
        <>
          <Card title="Shrnutí">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Stat label="Čistý zisk (účetní)" value={formatCurrency(cashflow.retained_profit)} />
              <Stat label="Čistý peněžní tok" value={formatCurrency(cashflow.net_cash_flow)} />
              <Stat label="Provozní CF" value={formatCurrency(cashflow.operating_cash_flow)} />
              <Stat label="Hrubá marže" value={formatCurrency(cashflow.gross_margin)} />
            </div>
          </Card>

          <Card title="Tabulka Zisk vs. peněžní tok">
            <Table
              headers={["Ukazatel", "Účetní pohled", "Peněžní tok", "Rozdíl"]}
              rows={tableRows}
              emptyMessage="Data nejsou k dispozici."
            />
          </Card>
        </>
      ) : (
        <Card title="Data nejsou dostupná">
          <p className="text-sm text-slate-500">Pro zvoleného uživatele zatím nejsou nahrány finanční výkazy.</p>
        </Card>
      )}
    </div>
  )
}

function buildCashflowRows(cf: CashflowData) {
  const revenueCash = cf.revenue * 0.93
  const cogsCash = cf.cogs * 0.98

  const rows: ReactNode[][] = []

  rows.push([
    "Tržby za prodej zboží a služeb",
    formatCurrency(cf.revenue),
    formatCurrency(revenueCash),
    formatCurrency(revenueCash - cf.revenue),
  ])

  rows.push([
    "Náklady na prodané zboží",
    formatCurrency(cf.cogs),
    formatCurrency(cogsCash),
    formatCurrency(cogsCash - cf.cogs),
  ])

  rows.push([
    "Hrubá marže",
    formatCurrency(cf.gross_margin),
    formatCurrency(cf.gross_cash_profit),
    formatCurrency(cf.variance.gross),
  ])

  rows.push([
    "Provozní zisk",
    formatCurrency(cf.operating_cash_profit),
    formatCurrency(cf.operating_cash_flow),
    formatCurrency(cf.variance.operating),
  ])

  rows.push([
    "Čistý zisk / Čistý cash flow",
    formatCurrency(cf.retained_profit),
    formatCurrency(cf.net_cash_flow),
    formatCurrency(cf.variance.net),
  ])

  rows.push([
    "Nákladové úroky",
    formatCurrency(-cf.interest),
    formatCurrency(-cf.interest),
    formatCurrency(0),
  ])

  rows.push([
    "Daně z příjmů",
    formatCurrency(cf.taxation),
    formatCurrency(cf.taxation),
    formatCurrency(0),
  ])

  rows.push([
    "Mimořádné výnosy",
    formatCurrency(cf.extraordinary),
    formatCurrency(cf.extraordinary),
    formatCurrency(0),
  ])

  rows.push([
    "Dividendy / podíly na zisku",
    formatCurrency(cf.dividends),
    formatCurrency(cf.dividends),
    formatCurrency(0),
  ])

  rows.push([
    "Odpisy dlouhodobého majetku",
    formatCurrency(-cf.depreciation),
    formatCurrency(-cf.fixed_assets),
    formatCurrency(cf.depreciation - cf.fixed_assets),
  ])

  if (cf.other_assets) {
    rows.push([
      "Nárůst ostatních aktiv",
      formatCurrency(-cf.other_assets),
      formatCurrency(0),
      formatCurrency(-cf.other_assets),
    ])
  }

  if (cf.capital_withdrawn) {
    rows.push([
      "Výběr základního kapitálu",
      formatCurrency(-cf.capital_withdrawn),
      formatCurrency(0),
      formatCurrency(-cf.capital_withdrawn),
    ])
  }

  return rows
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{value}</p>
    </div>
  )
}

function formatCurrency(value: number) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—"
  return `${value.toLocaleString("cs-CZ")} Kč`
}

