import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../../lib/apiClient'
import Card from '../../components/ui/Card'

type Question = {
  category: string
  question: string
  labels: Record<string, string>
}

type Submission = {
  batch_id: string
  created_at: string
  ai_response: string | null
  avg_score: number | null
}

type QuestionnaireResponse = {
  questions: Question[]
  submissions: Submission[]
}

type FormState = Record<number, number>

export default function SurveyPage() {
  const [data, setData] = useState<QuestionnaireResponse | null>(null)
  const [form, setForm] = useState<FormState>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    apiClient
      .get<QuestionnaireResponse>('/survey/api/questionnaire/')
      .then((res) => {
        if (!mounted) return
        setData(res)
        const initial: FormState = {}
        res.questions.forEach((_, idx) => {
          initial[idx] = 5
        })
        setForm(initial)
      })
      .catch((e: any) => {
        if (!mounted) return
        setError(e?.message || 'Nepodařilo se načíst dotazník.')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const submissions = useMemo(() => data?.submissions ?? [], [data])

  async function handleSubmit() {
    if (!data) return
    setSubmitting(true)
    setError(null)
    setSuccess(null)
    const answers = data.questions.map((_, idx) => form[idx] ?? 0)
    try {
      const res = await apiClient.post<{ submission: Submission }>('/survey/api/questionnaire/', { answers })
      setSuccess('Dotazník byl uložen. AI shrnutí bude k dispozici během chvíle.')
      setData((prev) =>
        prev
          ? {
              ...prev,
              submissions: [res.submission, ...prev.submissions],
            }
          : prev,
      )
    } catch (e: any) {
      setError(e?.message || 'Odeslání dotazníku selhalo.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading && !data) {
    return <p className="text-sm text-slate-500">Načítám dotazník…</p>
  }

  if (error && !data) {
    return <p className="text-sm text-red-600">{error}</p>
  }

  if (!data) return null

  return (
    <div className="space-y-8">
      <Card title="Dotazník ScaleupBoard" subtitle="Vyberte skóre 1–10.">
        <div className="space-y-6">
          {data.questions.map((question, idx) => {
            const score = form[idx] ?? 5
            const descriptor = Object.entries(question.labels).find(([range]) => {
              const [low, high] = range.split('-').map((value) => parseInt(value, 10))
              return score >= low && score <= high
            })?.[1]

            return (
              <div
                key={idx}
                className="space-y-3 rounded-xl border border-slate-200 dark:border-slate-800 p-4 bg-white dark:bg-slate-900"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      {question.category}
                    </p>
                    <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                      {question.question}
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-primary-600">{score}</span>
                    <input
                      type="range"
                      min={1}
                      max={10}
                      value={score}
                      onChange={(e) => setForm((prev) => ({ ...prev, [idx]: Number(e.target.value) }))}
                    />
                  </div>
                </div>
                {descriptor && <p className="text-sm text-slate-500 dark:text-slate-400">{descriptor}</p>}
              </div>
            )
          })}

          {error && <p className="text-sm text-red-600">{error}</p>}
          {success && <p className="text-sm text-emerald-600">{success}</p>}

          <button onClick={handleSubmit} className="btn-primary" disabled={submitting}>
            {submitting ? 'Odesílám…' : 'Odeslat dotazník'}
          </button>
        </div>
      </Card>

      <Card title="Historie dotazníků" subtitle="AI shrnutí a výsledky jednotlivých vln.">
        {submissions.length === 0 ? (
          <p className="text-sm text-slate-500">Zatím nemáte žádné odeslané dotazníky.</p>
        ) : (
          <div className="space-y-3">
            {submissions.map((submission) => (
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
                    Detail
                  </Link>
                </div>
                {submission.ai_response && (
                  <p className="mt-2 text-sm text-slate-500 dark:text-slate-300 line-clamp-3">
                    {submission.ai_response}
                  </p>
                )}
              </div>
            ))}
            <Link to="/survey/history" className="btn-ghost">
              Zobrazit celou historii
            </Link>
          </div>
        )}
      </Card>
    </div>
  )
}
