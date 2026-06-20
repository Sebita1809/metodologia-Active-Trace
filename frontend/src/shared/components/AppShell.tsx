import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/context/AuthContext'
import { useLogout } from '@/features/auth/hooks/useLogout'
import { NavMenu } from './NavMenu'

export function AppShell() {
  const { claims } = useAuth()
  const navigate = useNavigate()
  const logoutMutation = useLogout()

  const handleLogout = async () => {
    await logoutMutation.mutateAsync()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen bg-gray-100">
      {/* Sidebar */}
      <aside className="w-64 bg-white shadow-sm flex flex-col">
        {/* Brand */}
        <div className="px-6 py-4 border-b border-gray-200">
          <NavLink to="/dashboard" className="text-lg font-bold text-blue-600">
            active-trace
          </NavLink>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4 overflow-y-auto">
          <NavMenu />
        </nav>

        {/* User identity + logout */}
        <div className="px-4 py-4 border-t border-gray-200">
          {claims && (
            <div className="mb-3">
              <p className="text-xs text-gray-500 truncate">{claims.sub}</p>
              <p className="text-xs text-gray-400 truncate">
                {claims.roles.join(', ')}
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={handleLogout}
            disabled={logoutMutation.isPending}
            className="w-full text-left text-sm text-gray-600 hover:text-red-600 disabled:opacity-50 transition-colors"
          >
            {logoutMutation.isPending ? 'Cerrando sesión...' : 'Cerrar sesión'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {/* Top bar */}
        <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
          <div />
          {claims && (
            <span className="text-sm text-gray-600">{claims.sub}</span>
          )}
        </div>

        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
