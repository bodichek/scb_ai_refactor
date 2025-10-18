export type ApiOptions = {
  baseUrl?: string
}

const DEFAULT_BASE = import.meta.env.VITE_API_BASE_URL || ''

function getCookie(name: string) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop()!.split(';').shift()!
  return undefined
}

export function api(path: string, options: RequestInit = {}, cfg: ApiOptions = {}) {
  const base = cfg.baseUrl || DEFAULT_BASE
  const headers: HeadersInit = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  // Attach CSRF token if present (Django expects X-CSRFToken)
  const csrf = getCookie('csrftoken') || getCookie('CSRF-TOKEN')
  if (csrf && !('X-CSRFToken' in headers)) (headers as any)['X-CSRFToken'] = csrf

  return fetch(`${base}${path}`, {
    credentials: 'include',
    headers,
    ...options,
  })
}

export async function getJson<T>(path: string, init?: RequestInit) {
  const res = await api(path, { method: 'GET', ...(init || {}) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<T>
}

export async function postJson<T>(path: string, body: any, init?: RequestInit) {
  const res = await api(path, { method: 'POST', body: JSON.stringify(body), ...(init || {}) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<T>
}

export async function postForm<T>(path: string, form: FormData, init?: RequestInit) {
  const base = DEFAULT_BASE
  const csrf = getCookie('csrftoken') || getCookie('CSRF-TOKEN')
  const headers: HeadersInit = { ...(init?.headers || {}) }
  if (csrf) (headers as any)['X-CSRFToken'] = csrf
  const res = await fetch(`${base}${path}`, {
    method: 'POST',
    body: form,
    credentials: 'include',
    headers,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json() as Promise<T>
  // Return as any for non-JSON responses
  return ({} as unknown) as T
}
