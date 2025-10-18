import { useEffect, useState } from 'react'
import Card from '../../components/ui/Card'
import { getCSRFToken } from '../../lib/apiClient'

type ConfigResponse = {
  years: number[]
}

const SECTION_OPTIONS = [
  { value: 'charts', label: 'Grafy', description: 'Finanční grafy z dashboardu.' },
  { value: 'tables', label: 'Tabulky', description: 'Kompletní přehled dat včetně analýzy zisk vs. cashflow.' },
  { value: 'survey', label: 'Dotazník', description: 'Poslední vyplněný dotazník.' },
  { value: 'suropen', label: 'Osobní analýza', description: 'Odpovědi a shrnutí od AI.' },
]

/**
 * React přepis šablony exports/templates/exports/export_form.html.
 */
export default function ExportsPage() {
  const [years, setYears] = useState<number[]>([])
  const [year, setYear] = useState<number | null>(null)
  const [sections, setSections] = useState<Record<string, boolean>>({
    charts: true,
    tables: true,
    survey: false,
    suropen: false,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    fetch('/exports/api/config/', { credentials: 'include' })
      .then((res) => {
        if (!res.ok) throw new Error('Načtení konfigurace selhalo.')
        return res.json() as Promise<ConfigResponse>
      })
      .then((data) => {
        if (!mounted) return
        setYears(data.years)
        if (data.years.length > 0) setYear(data.years.at(-1) ?? null)
      })
      .catch((e: any) => {
        if (!mounted) return
        setError(e?.message || 'Nepodařilo se načíst konfiguraci exportu.')
      })
    return () => {
      mounted = false
    }
  }, [])

  async function handleSubmit() {
    if (!year) {
      setError('Vyberte prosím rok.')
      return
    }
    setLoading(true)
    setError(null)
    setSuccess(null)

    const form = new FormData()
    form.append('year', String(year))
    SECTION_OPTIONS.forEach((section) => {
      if (sections[section.value]) form.append('sections', section.value)
    })

    try {
      const csrf = getCSRFToken()
      const response = await fetch('/exports/pdf/', {
        method: 'POST',
        credentials: 'include',
        headers: csrf ? { 'X-CSRFToken': csrf } : {},
        body: form,
      })
      if (!response.ok) {
        const message = await response.text()
        throw new Error(message || 'Generování PDF selhalo.')
      }
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `scaleupboard_report_${year}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      setSuccess('PDF bylo vygenerováno a staženo.')
    } catch (e: any) {
      setError(e?.message || 'Generování PDF selhalo.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card title="Export do PDF" subtitle="Zvolte rok a sekce, které chcete zahrnout do reportu.">
        {error && <p className="text-sm text-red-600">{error}</p>}
        {success && <p className="text-sm text-emerald-600">{success}</p>}

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Rok</label>
            <select
              className="input w-48"
              value={year ?? ''}
              onChange={(e) => setYear(Number(e.target.value))}
              disabled={years.length === 0}
            >
              {years.length === 0 ? (
                <option value="" disabled>
                  Žádná data nejsou k dispozici
                </option>
              ) : (
                years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="space-y-3">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Sekce</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {SECTION_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className="flex flex-col gap-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4"
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={!!sections[option.value]}
                      onChange={(e) =>
                        setSections((prev) => ({ ...prev, [option.value]: e.target.checked }))
                      }
                    />
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                      {option.label}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{option.description}</p>
                </label>
              ))}
            </div>
          </div>

          <button onClick={handleSubmit} className="btn-primary" disabled={loading}>
            {loading ? 'Generuji…' : 'Vygenerovat PDF'}
          </button>
        </div>
      </Card>
    </div>
  )
}

