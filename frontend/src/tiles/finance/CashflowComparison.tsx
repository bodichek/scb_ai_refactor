import { useEffect, useState } from 'react'
import { api } from '../../lib/api'

type Props = {
  years: number[]
  selectedYear?: number
}

/**
 * React verze sekce „Zisk vs. peněžní tok“ z templates/dashboard/index.html.
 * Stále využívá HTML rendering z endpointu /dashboard/api/cashflow/<rok>/.
 */
export default function CashflowComparison({ years, selectedYear }: Props) {
  const [year, setYear] = useState<number>(selectedYear ?? years[0] ?? new Date().getFullYear())
  const [html, setHtml] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!year) return

    let cancelled = false
    setLoading(true)
    setError(null)

    api(`/dashboard/api/cashflow/${year}/`)
      .then(async (res) => {
        if (!cancelled) {
          const text = await res.text()
          setHtml(text)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || 'Nepodařilo se načíst cashflow analýzu.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [year])

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Zisk vs. peněžní tok</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Porovnání účetního zisku se skutečným peněžním tokem.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="cashflow-year" className="text-sm font-medium text-slate-600">
            Rok:
          </label>
          <select
            id="cashflow-year"
            className="input"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="min-h-[200px] rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
        {loading && <p className="text-sm text-slate-500">Načítám analýzu…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && (
          <div className="prose prose-sm max-w-none dark:prose-invert" dangerouslySetInnerHTML={{ __html: html }} />
        )}
      </div>
    </section>
  )
}

