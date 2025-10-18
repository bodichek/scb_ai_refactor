import { FormEvent, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Card from '../../components/ui/Card'
import apiClient, { ApiError } from '../../lib/apiClient'

type LoginResponse = {
  success: boolean
  redirect?: string
  error?: string
}

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = (location.state as { from?: string })?.from || '/'

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const response = await apiClient.post<LoginResponse>('/accounts/api/login/', {
        username,
        password,
      })

      if (response.redirect) {
        window.location.href = response.redirect
        return
      }

      navigate(redirectTo, { replace: true })
    } catch (err) {
      const apiErr = err as ApiError
      setError(apiErr.message || 'Přihlášení selhalo.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="w-full max-w-md">
        <Card title="Přihlášení" subtitle="Vložte přihlašovací údaje ke ScaleupBoard.">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium text-slate-600 dark:text-slate-200">
                E-mail
              </label>
              <input
                id="username"
                type="email"
                className="input w-full"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-slate-600 dark:text-slate-200">
                Heslo
              </label>
              <input
                id="password"
                type="password"
                className="input w-full"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
              />
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? 'Přihlašuji…' : 'Přihlásit se'}
            </button>
          </form>
        </Card>
      </div>
    </div>
  )
}
