import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import Card from '../../components/ui/Card'
import AllMetricsTable, { DashboardRow } from '../../tiles/finance/AllMetricsTable'
import LineChartCard from '../../components/charts/LineChartCard'
import Table from '../../components/ui/Table'
import apiClient from '../../lib/apiClient'

type ChartRow = {
  year: number
  revenue: number
  cogs: number
  gross_margin: number
  overheads: number
  depreciation: number
  ebit: number
  net_profit: number
  profitability: {
    gm_pct: number
    op_pct: number
    np_pct: number
  }
  growth?: {
    revenue: number
    cogs: number
    overheads: number
  }
}

type CashflowSummary = {
  revenue: number
  gross_cash_profit: number
  operating_cash_profit: number
  operating_cash_flow: number
  retained_profit: number
  net_cash_flow: number
  variance: {
    gross: number
    operating: number
    net: number
  }
  available_years: number[]
  current_year: number | null
}

type ClientOverview = {
  client: {
    id: number
    company_name: string
    user: {
      first_name: string
      last_name: string
      email: string
    }
  }
  statements_count: number
  documents_count: number
  surveys_completed: number
  days_since_activity: number | null
  has_cashflow_data: boolean
  cashflow: CashflowSummary | null
  chart_data: ChartRow[]
  table_rows: DashboardRow[]
  survey_details: any[]
  suropen_answers: any[]
  financial_statements: {
    id: number
    filename: string
    uploaded_at: string
    file_url: string
    get_doc_type_display: string
  }[]
  other_documents: {
    id: number
    filename: string
    uploaded_at: string
    file_url: string
    get_doc_type_display: string
  }[]
  client_notes?: string
}

type ClientResponse = ClientOverview & { success?: boolean; error?: string }

export default function CoachClientDetailPage() {
  const { clientId } = useParams()
  const [data, setData] = useState<ClientOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [notesSaved, setNotesSaved] = useState<string | null>(null)

  useEffect(() => {
    if (!clientId) return
    let mounted = true
    setLoading(true)
    setError(null)

    fetch(`/coaching/client/${clientId}/`, {
      credentials: 'include',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'application/json',
      },
    })
      .then(async (res) => {
        const payload = (await res.json()) as ClientResponse
        if (!mounted) return
        if (!res.ok || payload.error) {
          throw new Error(payload.error || `HTTP ${res.status}`)
        }
        setData(payload)
        setNotes(payload.client_notes || '')
      })
      .catch((e: any) => {
        if (mounted) setError(e?.message || 'Nepodařilo se načíst detail klienta.')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [clientId])

  const chartRows = useMemo(() => data?.chart_data ?? [], [data])
  const metricsRows = useMemo(() => data?.table_rows ?? [], [data])

  async function handleSaveNotes() {
    if (!clientId) return
    setSavingNotes(true)
    setNotesSaved(null)
    try {
      await apiClient.post(`/coaching/client/${clientId}/notes/`, { notes })
      setNotesSaved('Poznámky byly uloženy.')
    } catch (e: any) {
      setError(e?.message || 'Uložení poznámek selhalo.')
    } finally {
      setSavingNotes(false)
    }
  }

  if (loading && !data) return <p className="text-sm text-slate-500">Načítám detail…</p>
  if (error && !data) return <p className="text-sm text-red-600">{error}</p>
  if (!data) return null

  return (
    <div className="space-y-6">
      <Card
        title={data.client.company_name || 'Klient'}
        subtitle={`${data.client.user.first_name} ${data.client.user.last_name} · ${data.client.user.email}`}
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Finanční výkazy" value={data.statements_count} />
          <Stat label="Dokumenty" value={data.documents_count} />
          <Stat label="Dotazníky" value={data.surveys_completed} />
          <Stat label="Dny od aktivity" value={data.days_since_activity ?? '—'} />
        </div>
      </Card>

      <Card title="Poznámky kouče" subtitle="Tyto poznámky vidíte jen vy.">
        <textarea
          className="w-full min-h-[140px] rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm focus:border-primary-500 focus:ring-primary-500"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <div className="mt-3 flex items-center gap-3">
          <button className="btn-primary" onClick={handleSaveNotes} disabled={savingNotes}>
            {savingNotes ? 'Ukládám…' : 'Uložit poznámky'}
          </button>
          {notesSaved && <p className="text-sm text-emerald-600">{notesSaved}</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
      </Card>

      {chartRows.length > 0 && (
        <LineChartCard
          title="Finanční vývoj"
          subtitle="Tržby, COGS a EBIT dle roku."
          data={chartRows}
          xKey="year"
          lines={[
            { dataKey: 'revenue', name: 'Tržby', color: '#2563eb' },
            { dataKey: 'cogs', name: 'COGS', color: '#ef4444' },
            { dataKey: 'ebit', name: 'EBIT', color: '#22c55e' },
          ]}
        />
      )}

      {metricsRows.length > 0 && (
        <Card title="Tabulkový přehled">
          <AllMetricsTable rows={metricsRows} />
        </Card>
      )}

      {data.cashflow && (
        <Card
          title="Zisk vs. peněžní tok"
          subtitle={`Rok ${data.cashflow.current_year ?? data.cashflow.available_years.at(-1) ?? '—'}`}
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 text-sm text-slate-600 dark:text-slate-300">
            <CashflowStat label="Zisk (retained profit)" value={data.cashflow.retained_profit} />
            <CashflowStat label="Čistý peněžní tok" value={data.cashflow.net_cash_flow} />
            <CashflowStat label="Hrubý peněžní zisk" value={data.cashflow.gross_cash_profit} />
            <CashflowStat label="Provozní CF" value={data.cashflow.operating_cash_flow} />
            <CashflowStat label="Provozní zisk" value={data.cashflow.operating_cash_profit} />
            <CashflowStat label="Tržby" value={data.cashflow.revenue} />
          </div>
        </Card>
      )}

      <Card title="Dokumenty" subtitle="Finanční výkazy a další soubory.">
        <Table
          headers={['Soubor', 'Typ', 'Nahrán', 'Akce']}
          rows={[
            ...(data.financial_statements ?? []).map((doc) => [
              doc.filename || '—',
              doc.get_doc_type_display,
              doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString('cs-CZ') : '—',
              doc.file_url ? (
                <a href={doc.file_url} target="_blank" rel="noopener" className="btn-ghost text-xs">
                  Otevřít
                </a>
              ) : (
                '—'
              ),
            ]),
            ...(data.other_documents ?? []).map((doc) => [
              doc.filename || '—',
              doc.get_doc_type_display,
              doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString('cs-CZ') : '—',
              doc.file_url ? (
                <a href={doc.file_url} target="_blank" rel="noopener" className="btn-ghost text-xs">
                  Otevřít
                </a>
              ) : (
                '—'
              ),
            ]),
          ]}
          emptyMessage="Žádné dokumenty."
        />
      </Card>

      <Card title="Dotazníky">
        {data.survey_details.length === 0 ? (
          <p className="text-sm text-slate-500">Žádné vyplněné dotazníky.</p>
        ) : (
          data.survey_details.map((item, idx) => (
            <div key={idx} className="space-y-2 rounded-xl border border-slate-200 dark:border-slate-800 p-4 bg-white dark:bg-slate-900 mb-4">
              <p className="text-sm text-slate-500">
                {new Date(item.submission.created_at).toLocaleString('cs-CZ')} · Průměr: {item.avg_score.toFixed(1)}
              </p>
              {item.submission.ai_response && (
                <p className="text-sm text-slate-600 dark:text-slate-300 whitespace-pre-line">
                  {item.submission.ai_response}
                </p>
              )}
            </div>
          ))
        )}
      </Card>

      <Card title="Suropen – osobní analýza">
        {data.suropen_answers.length === 0 ? (
          <p className="text-sm text-slate-500">Bez odevzdaných analýz.</p>
        ) : (
          data.suropen_answers.map((batch, idx) => (
            <div key={idx} className="space-y-2 rounded-xl border border-slate-200 dark:border-slate-800 p-4 bg-white dark:bg-slate-900 mb-4">
              <p className="text-sm text-slate-500">
                {batch.created_at ? new Date(batch.created_at).toLocaleString('cs-CZ') : '—'}
              </p>
              {batch.ai_response && (
                <p className="text-sm text-slate-600 dark:text-slate-300 whitespace-pre-line">
                  {batch.ai_response}
                </p>
              )}
            </div>
          ))
        )}
      </Card>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-xl font-semibold text-slate-900 dark:text-slate-100">{value}</p>
    </div>
  )
}

function CashflowStat({ label, value }: { label: string; value: number | null | undefined }) {
  const formatted = typeof value === 'number' ? `${value.toLocaleString('cs-CZ')} Kč` : '—'
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{formatted}</p>
    </div>
  )
}
