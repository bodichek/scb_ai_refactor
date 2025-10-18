import { useEffect, useState } from 'react'

type Theme = 'light' | 'dark'

function getSystemPrefersDark(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
}

function getStoredTheme(): Theme | null {
  try {
    const v = localStorage.getItem('theme')
    if (v === 'light' || v === 'dark') return v
    return null
  } catch {
    return null
  }
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'dark') root.classList.add('dark')
  else root.classList.remove('dark')
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>('light')

  useEffect(() => {
    const stored = getStoredTheme()
    const initial: Theme = stored ?? (getSystemPrefersDark() ? 'dark' : 'light')
    setTheme(initial)
    applyTheme(initial)
  }, [])

  function toggle() {
    setTheme((prev) => {
      const next: Theme = prev === 'dark' ? 'light' : 'dark'
      applyTheme(next)
      try { localStorage.setItem('theme', next) } catch {}
      return next
    })
  }

  return { theme, toggle }
}

