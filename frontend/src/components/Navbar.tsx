import { Bars3Icon, BellIcon, MoonIcon, SunIcon } from '@heroicons/react/24/outline'
import { useTheme } from '../lib/useTheme'

type Props = {
  onMenuClick?: () => void
}

export default function Navbar({ onMenuClick }: Props) {
  const { theme, toggle } = useTheme()

  return (
    <nav className="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-gray-200">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onMenuClick}
              className="md:hidden p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
              aria-label="Open menu"
            >
              <Bars3Icon className="h-6 w-6 text-gray-700 dark:text-gray-200" />
            </button>
            <div className="h-8 w-8 rounded-lg bg-primary-600 text-white grid place-items-center font-bold">S</div>
            <span className="text-lg font-semibold tracking-tight">ScaleupBoard</span>
          </div>

          <div className="flex items-center gap-3">
            <button className="p-2 rounded-full hover:bg-gray-100">
              <BellIcon className="h-6 w-6 text-gray-500" />
            </button>
            <button
              onClick={toggle}
              className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800"
              title={theme === 'dark' ? 'Světlý režim' : 'Tmavý režim'}
            >
              {theme === 'dark' ? (
                <SunIcon className="h-6 w-6 text-gray-600 dark:text-gray-300" />
              ) : (
                <MoonIcon className="h-6 w-6 text-gray-600" />
              )}
            </button>
          </div>
        </div>
      </div>
      <div className="h-1 bg-gradient-to-r from-primary-600 via-secondary-500 to-accent-500" />
    </nav>
  )
}

