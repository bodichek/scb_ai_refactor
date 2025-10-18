import { NavLink } from 'react-router-dom'
import {
  HomeIcon,
  ChartBarIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  ArrowUpTrayIcon,
  ArrowLeftOnRectangleIcon,
} from '@heroicons/react/24/outline'

function itemClass(isActive: boolean) {
  return [
    'flex items-center gap-3 px-3 py-2 rounded-md text-sm',
    isActive
      ? 'bg-gray-900 text-white dark:bg-gray-800'
      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800',
  ].join(' ')
}

type Props = {
  variant?: 'desktop' | 'mobile'
  onNavigate?: () => void
}

export default function Sidebar({ variant = 'desktop', onNavigate }: Props) {
  const isMobile = variant === 'mobile'
  const asideClass = isMobile
    ? 'fixed inset-y-0 left-0 z-50 md:hidden w-72 flex flex-col bg-white dark:bg-gray-900 shadow-xl'
    : 'hidden md:flex md:flex-col w-64 shrink-0 border-r border-gray-200 dark:border-gray-800 sticky top-16 h-[calc(100vh-4rem)] bg-white/70 dark:bg-gray-900/70 backdrop-blur'

  return (
    <aside className={asideClass} aria-label="Sidebar">
      <nav className="p-3 space-y-1 overflow-y-auto">
        <NavLink to="/" end className={({ isActive }) => itemClass(isActive)}>
          <HomeIcon className="h-5 w-5" />
          <span>Dashboard</span>
        </NavLink>
        <NavLink to="/finance" className={({ isActive }) => itemClass(isActive)}>
          <ChartBarIcon className="h-5 w-5" />
          <span>Finanční shrnutí</span>
        </NavLink>
        <NavLink to="/survey" className={({ isActive }) => itemClass(isActive)}>
          <ClipboardDocumentListIcon className="h-5 w-5" />
          <span>Dotazník</span>
        </NavLink>
        <NavLink to="/analysis" className={({ isActive }) => itemClass(isActive)}>
          <DocumentTextIcon className="h-5 w-5" />
          <span>Osobní analýza</span>
        </NavLink>
        <NavLink to="/export" className={({ isActive }) => itemClass(isActive)}>
          <ArrowUpTrayIcon className="h-5 w-5" />
          <span>Nahrat soubory</span>
        </NavLink>
      </nav>

      <div className="mt-auto p-3 border-t border-gray-200 dark:border-gray-800">
        <div className="space-y-1">
          <a href="/accounts/logout/" className={itemClass(false)} onClick={onNavigate}>
            <ArrowLeftOnRectangleIcon className="h-5 w-5" />
            <span>Odhlásit</span>
          </a>
        </div>
      </div>
    </aside>
  )
}
