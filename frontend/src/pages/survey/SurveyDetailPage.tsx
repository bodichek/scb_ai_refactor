import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ResponsiveContainer, Line, LineChart, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
import apiClient from '../../lib/apiClient'
import Card from '../../components/ui/Card'
import Table from '../../components/ui/Table'

type ResponseItem = {
  question: string
  score: number
  label: string | null
}

type SubmissionDetail = {
  batch_id: string
  created_at: string
  ai_response: string | null
  avg_score: number | null
  items: ResponseItem[]
}

type HistoryPoint = {
  label: string
  value: number
}

type DetailResponse = {
  submission: SubmissionDetail
  history: HistoryPoint[]
}

/**
 * React přepis šablony survey/templates/survey/detail.html.
 */
export default function SurveyDetailPage() {
  const { batchId } = useParams()
  const [data, setData] = useState<DetailResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!batchId) return
    let mounted = true
    setLoading(true)
    setError(null)

    apiClient
      .get<DetailResponse>(`/survey/api/submissions/${batchId}/`)
      .then((res) => {
        if (mounted) setData(res)
      })
      .catch((e: any) => {
        if (mounted) setError(e?.message || 'Nepodařilo se načíst detail dotazníku.')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [batchId])

  if (loading && !data) return <p className="text-sm text-slate-500">Načítám detail…</p>
  if (error && !data) return <p className="text-sm text-red-600">{error}</p>
  if (!data) return null

  const { submission, history } = data

  return (
    <div className="space-y-6">
      <Card title="Detail dotazníku" subtitle={new Date(submission.created_at).toLocaleString('cs-CZ')}>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Průměrné skóre: {submission.avg_score !== null ? submission.avg_score.toFixed(1) : 'N/A'}
        </p>
        {submission.ai_response ? (
          <div className="mt-4 space-y-2 text-sm text-slate-700 dark:text-slate-300">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">AI shrnutí:</h3>
            <p className="whitespace-pre-line">{submission.ai_response}</p>
          </div>
        ) : (
          <p className="mt-4 text-sm text-slate-500">Shrnutí ještě není k dispozici.</p>
        )}
      </Card>

      <Card title="Odpovědi">
        <Table
          headers={['Otázka', 'Skóre', 'Interpretace']}
          rows={submission.items.map((item) => [
            <span key="q" className="text-sm text-slate-800 dark:text-slate-200">
              {item.question}
            </span>,
            <span key="s" className="font-semibold text-slate-700 dark:text-slate-200">{item.score}</span>,
            <span key="l" className="text-sm text-slate-500 dark:text-slate-400">{item.label || '—'}</span>,
          ])}
        />
      </Card>

      <Card title="Historie průměrných skóre">
        {history.length === 0 ? (
          <p className="text-sm text-slate-500">Zatím žádná historie.</p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history} margin={{ top: 12, right: 24, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" name="Průměrné skóre" stroke="#2563eb" strokeWidth={2} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
    </div>
  )
}

