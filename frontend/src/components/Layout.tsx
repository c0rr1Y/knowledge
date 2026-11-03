import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import {
  LayoutDashboard,
  BookOpen,
  MessageSquare,
  LogOut,
  Leaf,
  Plus,
  ChevronDown,
  User,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { kbAPI } from '../api/client'
import type { KnowledgeBase } from '../types'

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => {
    kbAPI.list().then(setKbs).catch(console.error)
  }, [location.pathname])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-nature-gradient">
      {/* Top Navbar */}
      <nav className="bg-white/80 backdrop-blur-sm border-b border-nature-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 text-nature-800 hover:text-leaf-600 transition-colors">
            <div className="w-9 h-9 rounded-xl bg-leaf-500 flex items-center justify-center">
              <Leaf className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-lg tracking-tight">知识库</span>
          </Link>

          {/* User menu */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2.5 text-sm text-wood-500">
              <div className="w-8 h-8 rounded-full bg-leaf-100 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-leaf-600" />
              </div>
              <div className="hidden sm:block leading-tight">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-nature-800">{user?.username}</span>
                  {user?.tenant_name && (
                    <span className="px-2 py-0.5 rounded-full bg-leaf-50 text-leaf-700 text-xs font-medium border border-leaf-100">
                      {user.tenant_name}
                    </span>
                  )}
                </div>
                <div className="text-xs text-wood-400 mt-0.5">{user?.email}</div>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-sm text-wood-400 hover:text-red-500 transition-colors px-3 py-1.5 rounded-lg hover:bg-red-50"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">退出</span>
            </button>
          </div>
        </div>
      </nav>

      <div className="flex">
        {/* Sidebar */}
        <aside className={`bg-white/60 border-r border-nature-200 h-[calc(100vh-4rem)] sticky top-16 transition-all duration-300 ${
          sidebarOpen ? 'w-64' : 'w-16'
        }`}>
          <div className="p-4 flex flex-col h-full">
            {/* Navigation */}
            <nav className="space-y-1">
              <Link
                to="/"
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  location.pathname === '/'
                    ? 'bg-leaf-50 text-leaf-700 shadow-sm'
                    : 'text-wood-500 hover:bg-nature-100'
                }`}
              >
                <LayoutDashboard className="w-4 h-4 flex-shrink-0" />
                {sidebarOpen && <span>仪表盘</span>}
              </Link>

              <Link
                to="/chat"
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  location.pathname === '/chat'
                    ? 'bg-leaf-50 text-leaf-700 shadow-sm'
                    : 'text-wood-500 hover:bg-nature-100'
                }`}
              >
                <MessageSquare className="w-4 h-4 flex-shrink-0" />
                {sidebarOpen && <span>AI 问答</span>}
              </Link>
            </nav>

            {/* Knowledge Bases */}
            {sidebarOpen && (
              <div className="mt-6 flex-1 overflow-hidden flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-wood-400 uppercase tracking-wider">知识库</span>
                  <span className="text-xs text-wood-300">{kbs.length}</span>
                </div>
                <div className="space-y-0.5 overflow-y-auto flex-1">
                  {kbs.map(kb => (
                    <Link
                      key={kb.id}
                      to={`/kb/${kb.id}`}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
                        location.pathname.includes(`/kb/${kb.id}`)
                          ? 'bg-leaf-50 text-leaf-700 font-medium'
                          : 'text-wood-500 hover:bg-nature-100'
                      }`}
                    >
                      <BookOpen className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="truncate">{kb.name}</span>
                      <span className="ml-auto text-xs text-wood-300">{kb.document_count}</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Toggle sidebar */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="mt-auto text-wood-300 hover:text-wood-500 p-2"
            >
              <ChevronDown className={`w-4 h-4 transition-transform ${sidebarOpen ? 'rotate-0' : '-rotate-90'}`} />
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 min-h-[calc(100vh-4rem)]">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
