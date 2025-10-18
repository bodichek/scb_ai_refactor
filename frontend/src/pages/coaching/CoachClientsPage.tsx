import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../../lib/apiClient'
import Card from '../../components/ui/Card'
import Table from '../../components/ui/Table'

type ClientSummary = {
  id: number
  company_name: string
  user: {
    id: number
    first_name: string
    last_name: string
    email: string
  }
  statements_count: number
  last_activity: string | null
  days_since_activity: number | null
}

type ClientsApiResponse = {
  success: boolean
  search_query: string
  stats: {
    clients_count: number
    active_clients: number
    statements_total: number
    recent_uploads: number
  }
  clients: ClientSummary[]
  recent_activities: {
    date: string
    client_name: string
    description: string
  }[]
}

export default function CoachClientsPage() {
  const [data, setData] = useState<ClientsApiResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    let mounted = true
    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const res = await apiClient.get<ClientsApiResponse>(`/coaching/api/clients/?search=${encodeURIComponent(search)}`)
        if (mounted) setData(res)
      } catch (e: any) {
        if (mounted) setError(e?.message || 'Nepodařilo se načíst klienty.')
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchData()
    return () => {
      mounted = false
    }
  }, [search])

  const tableRows =
    data?.clients.map((client) => [
      <div key="client" className="space-y-1">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{client.company_name || '—'}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {client.user.first_name} {client.user.last_name} · {client.user.email}
        </p>
      </div>,
      client.statements_count,
      client.last_activity
        ? new Date(client.last_activity).toLocaleString('cs-CZ')
        : '—',
      client.days_since_activity !== null ? `${client.days_since_activity} dní` : '—',
      <Link key="detail" to={`/coaching/clients/${client.id}`} className="btn-secondary text-xs">
        Detail
      </Link>,
    ]) ?? []

  return (
    <div className="space-y-6">
      <Card title="Klienti" subtitle="Přehled všech klientů, kteří jsou vám přiřazeni.">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <input
            type="search"
            placeholder="Hledat firmu nebo kontakt…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input w-full max-w-sm"
          />
          {loading && <p className="text-sm text-slate-500">Načítám…</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4 mb-4">
          <Card title="Celkem klientů">
            <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              {data?.stats.clients_count ?? '—'}
            </p>
          </Card>
          <Card title="Aktivní (30 dní)">
            <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              {data?.stats.active_clients ?? '—'}
            </p>
          </Card>
          <Card title="Finanční výkazy">
            <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              {data?.stats.statements_total ?? '—'}
            </p>
          </Card>
          <Card title="Nahrávky za 30 dní">
            <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              {data?.stats.recent_uploads ?? '—'}
            </p>
          </Card>
        </div>

        <Table
          headers={['Klient', 'Výkazy', 'Poslední aktivita', 'Dny od aktivity', 'Akce']}
          rows={tableRows}
          emptyMessage="Zatím nemáte žádné klienty."
        />
      </Card>

      <Card title="Nedávná aktivita" subtitle="Poslední dokumenty nahrané vašimi klienty.">
        {data?.recent_activities?.length ? (
          <ul className="space-y-2">
            {data.recent_activities.map((activity, idx) => (
              <li key={idx} className="flex flex-col sm:flex-row sm:items-center sm:justify-between rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{activity.client_name}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{activity.description}</p>
                </div>
                <p className="text-xs text-slate-400">
                  {activity.date ? new Date(activity.date).toLocaleString('cs-CZ') : '—'}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">Žádná nedávná aktivita.</p>
        )}
      </Card>
    </div>
  )
}
