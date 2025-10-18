import { Bars3Icon, BellIcon, MoonIcon, SunIcon } from '@heroicons/react/24/outline'
import { useTheme } from '../lib/useTheme'

type NavbarProps = {
  onMenuToggle?: () => void
}

export function Navbar({ onMenuToggle }: NavbarProps) {
  const { theme, toggle } = useTheme()

  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-slate-200 dark:border-slate-800">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onMenuToggle}
              className="md:hidden p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              aria-label="Otevřít menu"
            >
              <Bars3Icon className="h-6 w-6 text-slate-700 dark:text-slate-200" />
            </button>
            <div className="h-8 w-8 rounded-xl bg-primary-600 text-white grid place-items-center font-semibold">
              S
            </div>
            <span className="text-lg font-semibold tracking-tight text-slate-800 dark:text-slate-100">
              ScaleupBoard
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition">
              <BellIcon className="h-6 w-6 text-slate-500 dark:text-slate-300" />
            </button>
            <button
              onClick={toggle}
              className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              title={theme === 'dark' ? 'Světlý režim' : 'Tmavý režim'}
            >
              {theme === 'dark' ? (
                <SunIcon className="h-6 w-6 text-slate-200" />
              ) : (
                <MoonIcon className="h-6 w-6 text-slate-600" />
              )}
            </button>
          </div>
        </div>
      </div>
      <div className="h-1 bg-gradient-to-r from-primary-500 via-secondary-500 to-accent-500" />
    </header>
  )
}

export default Navbar
