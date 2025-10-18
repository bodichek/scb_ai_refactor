import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../../lib/apiClient'
import Card from '../../components/ui/Card'

type Submission = {
  batch_id: string
  created_at: string
  ai_response: string | null
  avg_score: number | null
}

type Response = {
  submissions: Submission[]
}

/**
 * React přepis šablony survey/templates/survey/history.html.
 */
export default function SurveyHistoryPage() {
  const [data, setData] = useState<Response | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    apiClient
      .get<Response>('/survey/api/submissions/')
      .then((res) => {
        if (mounted) setData(res)
      })
      .catch((e: any) => {
        if (mounted) setError(e?.message || 'Nepodařilo se načíst historii.')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  if (loading && !data) return <p className="text-sm text-slate-500">Načítám historii…</p>
  if (error && !data) return <p className="text-sm text-red-600">{error}</p>
  if (!data) return null

  return (
    <div className="space-y-6">
      <Card title="Historie dotazníků" subtitle="Kompletní seznam všech odeslaných dotazníků.">
        <div className="space-y-3">
          {data.submissions.length === 0 ? (
            <p className="text-sm text-slate-500">Zatím žádné odeslané dotazníky.</p>
          ) : (
            data.submissions.map((submission) => (
              <div
                key={submission.batch_id}
                className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 bg-white dark:bg-slate-900"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
                      {new Date(submission.created_at).toLocaleString('cs-CZ')}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Průměrné skóre:{' '}
                      {submission.avg_score !== null ? submission.avg_score.toFixed(1) : 'N/A'}
                    </p>
                  </div>
                  <Link to={`/survey/${submission.batch_id}`} className="btn-secondary">
                    Zobrazit detail
                  </Link>
                </div>
                {submission.ai_response && (
                  <p className="mt-2 text-sm text-slate-500 dark:text-slate-300">{submission.ai_response}</p>
                )}
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  )
}

