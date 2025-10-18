import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import ChatWidget from '../components/ChatWidget'

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition">
      <Navbar onMenuToggle={() => setSidebarOpen(true)} />

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden bg-black/40"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      {sidebarOpen && (
        <Sidebar variant="mobile" onNavigate={() => setSidebarOpen(false)} />
      )}

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="md:flex md:gap-6">
          <Sidebar />
          <main className="flex-1 py-6">
            <Outlet />
          </main>
        </div>
      </div>
      <ChatWidget />
    </div>
  )
}

export default Layout
