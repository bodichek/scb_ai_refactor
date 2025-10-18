import { useRef, useState } from 'react'
import { postForm } from '../lib/api'

export default function FileUploadTile() {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [year, setYear] = useState<string>('2025')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f) setFile(f)
  }

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-lg p-6 text-center ${dragOver ? 'border-primary-500 bg-primary-50' : 'border-gray-300'}`}
      >
        <p className="text-sm text-gray-600">Přetáhněte soubor sem nebo</p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-2 px-3 py-1.5 text-sm rounded-md bg-gray-900 text-white hover:bg-gray-800"
        >
          Vyberte soubor
        </button>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
      </div>

      {file && (
        <div className="flex items-center justify-between rounded-md border border-gray-200 p-3">
          <div>
            <p className="text-sm font-medium text-gray-900">{file.name}</p>
            <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={2000}
              max={2100}
              value={year}
              onChange={(e) => setYear(e.target.value)}
              className="w-24 input"
              title="Rok"
            />
            <button
              type="button"
              disabled={loading}
              onClick={async () => {
                if (!file) return
                setLoading(true)
                setError(null)
                try {
                  const form = new FormData()
                  form.append('pdf_file', file)
                  form.append('year', year)
                  await postForm('/ingest/upload/', form)
                  alert('Soubor nahrán. Obnovte dashboard v backendu pro zobrazení změn.')
                } catch (e: any) {
                  setError(e?.message || 'Chyba nahrání')
                } finally {
                  setLoading(false)
                }
              }}
              className="btn-primary"
            >
              {loading ? 'Nahrávám...' : 'Nahrát'}
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}
