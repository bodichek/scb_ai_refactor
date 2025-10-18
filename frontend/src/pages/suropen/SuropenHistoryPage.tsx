import { useEffect, useState } from 'react'
import apiClient from '../../lib/apiClient'
import Card from '../../components/ui/Card'

type AnswerItem = {
  section: string
  question: string
  answer: string
}

type BatchDetail = {
  batch_id: string
  created_at: string | null
  ai_response: string | null
  answers: AnswerItem[]
}

type HistoryResponse = {
  batches: BatchDetail[]
}

/**
 * React přepis šablony suropen/templates/suropen/history.html.
 */
export default function SuropenHistoryPage() {
  const [data, setData] = useState<HistoryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    apiClient
      .get<HistoryResponse>('/suropen/api/history/')
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
      {data.batches.length === 0 ? (
        <Card title="Historie">
          <p className="text-sm text-slate-500">Zatím nemáte žádné uložené odpovědi.</p>
        </Card>
      ) : (
        data.batches.map((batch) => (
          <Card
            key={batch.batch_id}
            title={batch.created_at ? new Date(batch.created_at).toLocaleString('cs-CZ') : '—'}
            subtitle={`Počet odpovědí: ${batch.answers.length}`}
          >
            {batch.ai_response && (
              <div className="mb-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">AI shrnutí:</h3>
                <p className="whitespace-pre-line">{batch.ai_response}</p>
              </div>
            )}
            <div className="space-y-4">
              {batch.answers.map((answer, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 bg-white dark:bg-slate-900"
                >
                  <p className="text-xs font-semibold uppercase text-slate-500">{answer.section}</p>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{answer.question}</p>
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-300 whitespace-pre-line">
                    {answer.answer || '—'}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        ))
      )}
    </div>
  )
}

