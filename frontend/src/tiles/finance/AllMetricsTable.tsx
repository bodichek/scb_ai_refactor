import Table from '../../components/ui/Table'

export type DashboardRow = {
  year: number
  revenue: number
  cogs: number
  gross_margin: number
  overheads: number
  ebit: number
  net_profit: number
  profitability: {
    gm_pct: number
    op_pct: number
    np_pct: number
  }
  growth: {
    revenue: number
    cogs: number
    overheads: number
  }
}

type Props = {
  rows: DashboardRow[]
}

/**
 * React verze tabulky z templates/dashboard/index.html.
 */
export default function AllMetricsTable({ rows }: Props) {
  const headers = [
    'Rok',
    'Tržby (Kč)',
    'Náklady na prodané zboží (Kč)',
    'Hrubá marže (Kč)',
    'Provozní náklady (Kč)',
    'EBIT (Kč)',
    'Čistý zisk (Kč)',
    'Hrubá marže %',
    'Provozní marže %',
    'Čistá marže %',
    'Růst tržeb %',
    'Růst COGS %',
    'Růst provozních nákladů %',
  ]

  const tableRows = rows.map((row) => [
    row.year,
    row.revenue.toLocaleString('cs-CZ'),
    row.cogs.toLocaleString('cs-CZ'),
    row.gross_margin.toLocaleString('cs-CZ'),
    row.overheads.toLocaleString('cs-CZ'),
    row.ebit.toLocaleString('cs-CZ'),
    row.net_profit.toLocaleString('cs-CZ'),
    `${row.profitability.gm_pct.toFixed(2)} %`,
    `${row.profitability.op_pct.toFixed(2)} %`,
    `${row.profitability.np_pct.toFixed(2)} %`,
    `${row.growth.revenue.toFixed(2)} %`,
    `${row.growth.cogs.toFixed(2)} %`,
    `${row.growth.overheads.toFixed(2)} %`,
  ])

  return <Table headers={headers} rows={tableRows} emptyMessage="Žádná data pro zvolená období." />
}

