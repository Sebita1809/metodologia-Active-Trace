import type { ReactNode } from 'react'
import { useAuth } from '@/features/auth/context/AuthContext'
import type { Role } from '@/shared/services/jwtDecode'

interface RequireRoleProps {
  roles: Role[]
  children: ReactNode
}

function AccessDenied() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          Acceso denegado
        </h2>
        <p className="text-gray-500 text-sm">
          No tenés permisos para ver esta sección.
        </p>
      </div>
    </div>
  )
}

export function RequireRole({ roles, children }: RequireRoleProps) {
  const { claims } = useAuth()

  if (!claims) return <AccessDenied />

  const hasRole = roles.some((role) => claims.roles.includes(role))
  if (!hasRole) return <AccessDenied />

  return <>{children}</>
}
