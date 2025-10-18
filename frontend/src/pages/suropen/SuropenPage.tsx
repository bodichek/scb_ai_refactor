import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../../lib/apiClient'
import Card from '../../components/ui/Card'
import Table from '../../components/ui/Table'

type QuestionBlock = {
  section: string
  items: string[]
}

type SubmissionSummary = {
  batch_id: string
  created_at: string | null
  answer_count: number
  ai_response: string | null
}

type FormResponse = {
  questions: QuestionBlock[]
  submissions: SubmissionSummary[]
  cooldown_seconds: number
}

type FormAnswer = Record<string, string>

/**
 * React přepis šablony suropen/templates/suropen/form.html.
 */
export default function SuropenPage() {
  const [data, setData] = useState<FormResponse | null>(null)
  const [form, setForm] = useState<FormAnswer>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    apiClient
      .get<FormResponse>('/suropen/api/form/')
      .then((res) => {
        if (!mounted) return
        setData(res)
        const initial: FormAnswer = {}
        res.questions.forEach((block, sIdx) =>
          block.items.forEach((_, qIdx) => {
            initial[`${sIdx}-${qIdx}`] = ''
          }),
        )
        setForm(initial)
      })
      .catch((e: any) => {
        if (!mounted) return
        setError(e?.message || 'Nepodařilo se načíst formulář.')
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
    const answers = data.questions.flatMap((block, sIdx) =>
      block.items.map((question, qIdx) => ({
        section: block.section,
        question,
        answer: (form[`${sIdx}-${qIdx}`] || '').trim(),
      })),
    )
    try {
      const res = await apiClient.post<{ submission: SubmissionSummary }>('/suropen/api/form/', { answers })
      setSuccess('Odpovědi byly uloženy. AI shrnutí bude dostupné během chvíle.')
      setData((prev) =>
        prev
          ? {
              ...prev,
              submissions: [res.submission, ...prev.submissions],
            }
          : prev,
      )
      const cleared: FormAnswer = {}
      Object.keys(form).forEach((key) => {
        cleared[key] = ''
      })
      setForm(cleared)
    } catch (e: any) {
      const message = e?.message || 'Odeslání selhalo.'
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading && !data) {
    return <p className="text-sm text-slate-500">Načítám data…</p>
  }

  if (error && !data) {
    return <p className="text-sm text-red-600">{error}</p>
  }

  if (!data) return null

  const summaryRows = submissions.map((submission) => [
    <div key="created" className="space-y-1">
      <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
        {submission.created_at ? new Date(submission.created_at).toLocaleString('cs-CZ') : '—'}
      </p>
      <p className="text-xs text-slate-500">{submission.answer_count} odpovědí</p>
    </div>,
    submission.ai_response ? (
      <p key="ai" className="text-sm text-slate-500 line-clamp-3">
        {submission.ai_response}
      </p>
    ) : (
      <span key="pending" className="text-xs text-amber-600">
        Shrnutí se připravuje…
      </span>
    ),
    <Link key="history" to="/suropen/history" className="btn-ghost text-xs">
      Celá historie
    </Link>,
  ])

  return (
    <div className="space-y-8">
      <Card title="Suropen" subtitle="Zpětná vazba pro zakladatele. Odpovědi jsou otevřené, AI je shrne.">
        <div className="space-y-6">
          {data.questions.map((block, sIdx) => (
            <div key={block.section} className="space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                {block.section}
              </h3>
              {block.items.map((question, qIdx) => {
                const key = `${sIdx}-${qIdx}`
                return (
                  <div key={key} className="space-y-2">
                    <label className="text-sm font-medium text-slate-700 dark:text-slate-200">{question}</label>
                    <textarea
                      value={form[key] ?? ''}
                      onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
                      className="w-full min-h-[120px] rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-3 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500"
                      placeholder="Vaše odpověď…"
                    />
                  </div>
                )
              })}
            </div>
          ))}

          {error && <p className="text-sm text-red-600">{error}</p>}
          {success && <p className="text-sm text-emerald-600">{success}</p>}

          <button onClick={handleSubmit} className="btn-primary" disabled={submitting}>
            {submitting ? 'Odesílám…' : 'Odeslat odpovědi'}
          </button>
          <p className="text-xs text-slate-400">
            Ochrana proti duplicitám: nové odeslání lze nejdříve za {data.cooldown_seconds} sekund.
          </p>
        </div>
      </Card>

      <Card title="Poslední shrnutí" subtitle="AI zpětná vazba z vašich předchozích odpovědí.">
        {summaryRows.length === 0 ? (
          <p className="text-sm text-slate-500">Zatím nemáte žádné odeslané odpovědi.</p>
        ) : (
          <Table headers={['Datum', 'AI shrnutí', 'Akce']} rows={summaryRows} />
        )}
      </Card>
    </div>
  )
}

