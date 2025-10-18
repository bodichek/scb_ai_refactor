const DEFAULT_BASE = import.meta.env.VITE_API_BASE_URL || ''

export type ApiError = {
  message: string
  status: number
  isAuthError?: boolean
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop()!.split(';').shift() || null
  return null
}

export function getCSRFToken(): string | null {
  return getCookie('csrftoken') || getCookie('CSRF-TOKEN')
}

async function request<T>(input: RequestInfo, init: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(init.headers || {}),
  }

  const method = (init.method || 'GET').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrf = getCSRFToken()
    if (csrf) headers['X-CSRFToken'] = csrf
  }

  const response = await fetch(`${DEFAULT_BASE}${input}`, {
    credentials: 'include',
    ...init,
    headers,
  })

  if (response.status === 401) {
    throw {
      message: 'Přihlášení vypršelo. Přihlaste se prosím znovu.',
      status: response.status,
      isAuthError: true,
    } as ApiError
  }

  if (!response.ok) {
    const text = await response.text()
    throw { message: text || response.statusText, status: response.status } as ApiError
  }

  if (response.status === 204) {
    return undefined as unknown as T
  }

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json() as Promise<T>
  }

  const text = await response.text()
  const isHtml = text.trimStart().toLowerCase().startsWith('<!doctype') || contentType.includes('text/html')
  const message = isHtml
    ? 'Server vrátil HTML místo JSON. Zkontrolujte, zda jste přihlášeni.'
    : text || 'Server vrátil neočekávanou odpověď.'

  throw { message, status: response.status } as ApiError
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: any, init?: RequestInit) =>
    request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body),
      ...init,
    }),
}

export default apiClient
