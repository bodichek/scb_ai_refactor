import { useEffect, useMemo, useState } from 'react'
import Card from '../../components/ui/Card'
import Table from '../../components/ui/Table'
import apiClient, { getCSRFToken } from '../../lib/apiClient'
import { postForm } from '../../lib/api'

type DocumentItem = {
  id: number
  filename: string
  year: number
  doc_type: string
  doc_type_display: string
  analyzed: boolean
  uploaded_at: string
  last_updated: string | null
  url: string
}

type DocumentsResponse = {
  scope: 'latest' | 'all'
  documents: DocumentItem[]
}

type UploadResult = {
  file: string
  year: number | null
  type: string | null
  status: string
  success: boolean
}

const scopeOptions = [
  { value: 'latest', label: 'Nejnovější výkazy' },
  { value: 'all', label: 'Všechny soubory' },
]

/**
 * React přepis šablony ingest/templates/ingest/documents_list.html.
 */
export default function IngestPage() {
  const [scope, setScope] = useState<'latest' | 'all'>('latest')
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([])

  useEffect(() => {
    loadDocuments(scope)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope])

  async function loadDocuments(nextScope: 'latest' | 'all') {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<DocumentsResponse>(`/ingest/api/documents/?scope=${nextScope}`)
      setDocuments(res.documents)
    } catch (e: any) {
      setError(e?.message || 'Nepodařilo se načíst seznam dokumentů.')
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return
    const form = new FormData()
    Array.from(files).forEach((file) => form.append('pdf_files', file))

    setUploading(true)
    setError(null)
    setUploadResults([])
    try {
      const res = await postForm<{ success: boolean; results: UploadResult[] }>('/ingest/api/documents/', form)
      setUploadResults(res.results)
      await loadDocuments(scope)
    } catch (e: any) {
      setError(e?.message || 'Nahrávání dokumentů selhalo.')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(id: number) {
    const csrf = getCSRFToken()
    try {
      const res = await fetch(`/ingest/api/documents/${id}/`, {
        method: 'DELETE',
        credentials: 'include',
        headers: csrf ? { 'X-CSRFToken': csrf } : {},
      })
      if (!res.ok) {
        throw new Error(await res.text())
      }
      setDocuments((prev) => prev.filter((doc) => doc.id !== id))
    } catch (e: any) {
      setError(e?.message || 'Smazání dokumentu selhalo.')
    }
  }

  const tableRows = useMemo(
    () =>
      documents.map((doc) => [
        <div key="name" className="space-y-1">
          <a href={doc.url} target="_blank" rel="noopener" className="text-primary-600 hover:underline">
            {doc.filename}
          </a>
          <p className="text-xs text-slate-500">{doc.doc_type_display}</p>
        </div>,
        doc.year,
        doc.analyzed ? (
          <span key="analyzed" className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
            Analyzováno
          </span>
        ) : (
          <span key="analyzed" className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
            Čeká na analýzu
          </span>
        ),
        new Date(doc.uploaded_at).toLocaleString('cs-CZ'),
        doc.last_updated ? new Date(doc.last_updated).toLocaleString('cs-CZ') : '—',
        <button key="actions" className="btn-ghost text-xs" onClick={() => handleDelete(doc.id)}>
          Smazat
        </button>,
      ]),
    [documents],
  )

  return (
    <div className="space-y-6">
      <Card title="Nahrát dokumenty" subtitle="PDF výkazy (rozvaha, výsledovka, cashflow). AI je rozpozná a zanalyzuje.">
        <div className="flex flex-wrap gap-4">
          <label className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-6 py-8 text-sm text-slate-500 w-full sm:w-auto">
            <span>Přetáhněte nebo vyberte soubory</span>
            <span className="text-xs text-slate-400">Podporováno více souborů najednou</span>
            <input
              type="file"
              accept="application/pdf"
              multiple
              className="hidden"
              onChange={(e) => handleUpload(e.target.files)}
              disabled={uploading}
            />
          </label>
          {uploading && <p className="text-sm text-slate-500">Nahrávám a zpracovávám…</p>}
        </div>
        {uploadResults.length > 0 && (
          <div className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
            {uploadResults.map((res, idx) => (
              <p key={idx} className={res.success ? 'text-emerald-600' : 'text-red-600'}>
                {res.file}: {res.status}
              </p>
            ))}
          </div>
        )}
      </Card>

      <Card title="Dokumenty" subtitle="Výkazy připojené k vašemu účtu.">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <span className="text-sm text-slate-600">Zobrazení:</span>
          {scopeOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setScope(option.value as 'latest' | 'all')}
              className={
                scope === option.value
                  ? 'btn-primary text-xs'
                  : 'btn-ghost text-xs text-slate-600 dark:text-slate-300'
              }
              disabled={scope === option.value}
            >
              {option.label}
            </button>
          ))}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Načítám dokumenty…</p>
        ) : (
          <Table
            headers={['Soubor', 'Rok', 'Stav', 'Nahrán', 'Aktualizováno', 'Akce']}
            rows={tableRows}
            emptyMessage="Zatím nemáte žádné dokumenty."
          />
        )}
      </Card>
    </div>
  )
}

