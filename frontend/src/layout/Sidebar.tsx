import { NavLink } from 'react-router-dom'
import {
  HomeIcon,
  ChartBarIcon,
  ClipboardDocumentListIcon,
  DocumentTextIcon,
  ArrowUpTrayIcon,
  ChatBubbleLeftEllipsisIcon,
  SparklesIcon,
  UserGroupIcon,
  RectangleGroupIcon,
} from '@heroicons/react/24/outline'

type SidebarProps = {
  variant?: 'desktop' | 'mobile'
  onNavigate?: () => void
}

function navItemClass(isActive: boolean) {
  return [
    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium',
    isActive
      ? 'bg-primary-600 text-white shadow'
      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800',
  ].join(' ')
}

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: HomeIcon },
  { to: '/dashboard/cashflow', label: 'Cashflow', icon: SparklesIcon },
  { to: '/dashboard/profitability', label: 'Ziskovost', icon: ChartBarIcon },
  { to: '/ingest', label: 'Dokumenty', icon: RectangleGroupIcon },
  { to: '/survey', label: 'Dotazník', icon: ClipboardDocumentListIcon },
  { to: '/suropen', label: 'Osobní analýza', icon: DocumentTextIcon },
  { to: '/exports', label: 'Nahrát soubory', icon: ArrowUpTrayIcon },
  { to: '/chatbot', label: 'Chatbot', icon: ChatBubbleLeftEllipsisIcon },
  { to: '/coaching', label: 'Coaching', icon: UserGroupIcon },
]

export function Sidebar({ variant = 'desktop', onNavigate }: SidebarProps) {
  const isMobile = variant === 'mobile'
  const wrapperClass = isMobile
    ? 'fixed inset-y-0 left-0 z-50 md:hidden w-72 bg-white dark:bg-slate-900 shadow-xl flex flex-col'
    : 'hidden md:flex md:flex-col w-64 shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur h-[calc(100vh-4rem)] sticky top-16'

  return (
    <aside className={wrapperClass} aria-label="Postranní panel">
      <nav className="flex-1 overflow-y-auto p-4 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => navItemClass(isActive)}
            onClick={onNavigate}
          >
            <Icon className="h-5 w-5" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-200 dark:border-slate-800 p-4">
        <a
          href="/accounts/logout/"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <ArrowUpTrayIcon className="h-5 w-5 rotate-180" />
          <span>Odhlásit</span>
        </a>
      </div>
    </aside>
  )
}

export default Sidebar
