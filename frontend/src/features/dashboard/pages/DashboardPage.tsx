import { useAuth } from '@/features/auth/context/AuthContext'

export function DashboardPage() {
  const { claims } = useAuth()

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-gray-900 mb-4">Dashboard</h1>
      {claims && (
        <p className="text-gray-600 text-sm">
          Bienvenido — roles activos:{' '}
          <span className="font-medium">{claims.roles.join(', ')}</span>
        </p>
      )}
    </div>
  )
}
