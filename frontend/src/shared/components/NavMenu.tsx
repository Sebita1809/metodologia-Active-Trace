import { NavLink } from 'react-router-dom'
import { useAuth } from '@/features/auth/context/AuthContext'
import type { Role } from '@/shared/services/jwtDecode'

interface NavItem {
  label: string
  to: string
  roles: Role[] | 'all'
}

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Dashboard',
    to: '/dashboard',
    roles: 'all',
  },
  {
    label: 'Comisión',
    to: '/comision',
    roles: ['TUTOR', 'PROFESOR'],
  },
  {
    label: 'Gestión',
    to: '/gestion',
    roles: ['ADMIN', 'COORDINADOR'],
  },
  {
    label: 'Alumnos',
    to: '/alumnos',
    roles: ['TUTOR', 'PROFESOR', 'COORDINADOR', 'ADMIN', 'NEXO'],
  },
]

// Coordinación section — shown only for COORDINADOR / ADMIN (C-23)
const COORD_NAV_ITEMS: NavItem[] = [
  {
    label: 'Equipos',
    to: '/coordinacion/equipos',
    roles: ['COORDINADOR', 'ADMIN'],
  },
  {
    label: 'Avisos',
    to: '/coordinacion/avisos',
    roles: ['COORDINADOR', 'ADMIN'],
  },
  {
    label: 'Encuentros',
    to: '/coordinacion/encuentros',
    roles: ['COORDINADOR', 'ADMIN'],
  },
  {
    label: 'Coloquios',
    to: '/coordinacion/coloquios',
    roles: ['COORDINADOR', 'ADMIN'],
  },
  {
    label: 'Monitor general',
    to: '/coordinacion/monitor-general',
    roles: ['COORDINADOR', 'ADMIN'],
  },
  {
    label: 'Aprobación comunicaciones',
    to: '/coordinacion/comunicaciones/aprobacion',
    roles: ['COORDINADOR', 'ADMIN'],
  },
]

// Tareas — shared between roles (C-23)
const SHARED_NAV_ITEMS: NavItem[] = [
  {
    label: 'Tareas',
    to: '/tareas',
    roles: ['TUTOR', 'PROFESOR', 'COORDINADOR', 'ADMIN'],
  },
]

// Finanzas section (C-24) — FINANZAS and ADMIN
const FINANZAS_NAV_ITEMS: NavItem[] = [
  {
    label: 'Liquidaciones',
    to: '/finanzas/liquidaciones',
    roles: ['FINANZAS', 'ADMIN'],
  },
  {
    label: 'Grilla salarial',
    to: '/finanzas/grilla-salarial',
    roles: ['FINANZAS'],
  },
  {
    label: 'Facturas',
    to: '/finanzas/facturas',
    roles: ['FINANZAS'],
  },
]

// Admin section (C-24) — ADMIN only (programas-fechas: ADMIN + COORDINADOR)
const ADMIN_NAV_ITEMS: NavItem[] = [
  {
    label: 'Estructura académica',
    to: '/admin/estructura',
    roles: ['ADMIN'],
  },
  {
    label: 'Usuarios',
    to: '/admin/usuarios',
    roles: ['ADMIN'],
  },
  {
    label: 'Programas y fechas',
    to: '/admin/programas-fechas',
    roles: ['ADMIN', 'COORDINADOR'],
  },
]

// Auditoría (C-24) — COORDINADOR and ADMIN
const AUDITORIA_NAV_ITEMS: NavItem[] = [
  {
    label: 'Auditoría',
    to: '/auditoria',
    roles: ['COORDINADOR', 'ADMIN'],
  },
]

function NavLinkItem({ to, label }: { to: string; label: string }) {
  return (
    <li>
      <NavLink
        to={to}
        className={({ isActive }) =>
          [
            'block px-3 py-2 rounded text-sm font-medium transition-colors',
            isActive
              ? 'bg-blue-50 text-blue-700'
              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
          ].join(' ')
        }
      >
        {label}
      </NavLink>
    </li>
  )
}

function NavSection({
  title,
  items,
}: {
  title: string
  items: NavItem[]
}) {
  if (items.length === 0) return null
  return (
    <div>
      <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
        {title}
      </p>
      <ul className="space-y-1">
        {items.map((item) => (
          <NavLinkItem key={item.to} to={item.to} label={item.label} />
        ))}
      </ul>
    </div>
  )
}

export function NavMenu() {
  const { claims } = useAuth()

  const userRoles = claims?.roles ?? []

  function filterItems(items: NavItem[]) {
    if (!claims) return []
    return items.filter((item) => {
      if (item.roles === 'all') return true
      return item.roles.some((role) => userRoles.includes(role))
    })
  }

  const visibleItems = NAV_ITEMS.filter((item) => {
    if (item.roles === 'all') return true
    if (!claims) return false
    return item.roles.some((role) => userRoles.includes(role))
  })

  const visibleShared = SHARED_NAV_ITEMS.filter((item) =>
    item.roles.some((role) => userRoles.includes(role)),
  )

  const visibleCoord = COORD_NAV_ITEMS.filter((item) =>
    item.roles.some((role) => userRoles.includes(role)),
  )

  const visibleFinanzas = filterItems(FINANZAS_NAV_ITEMS)
  const visibleAdmin = filterItems(ADMIN_NAV_ITEMS)
  const visibleAuditoria = filterItems(AUDITORIA_NAV_ITEMS)

  const showCoordSection = visibleCoord.length > 0

  return (
    <nav className="space-y-4">
      <ul className="space-y-1">
        {visibleItems.map((item) => (
          <NavLinkItem key={item.to} to={item.to} label={item.label} />
        ))}
        {visibleShared.map((item) => (
          <NavLinkItem key={item.to} to={item.to} label={item.label} />
        ))}
      </ul>

      {/* Coordinación section */}
      {showCoordSection && (
        <NavSection title="Coordinación" items={visibleCoord} />
      )}

      {/* Finanzas section (C-24) */}
      {visibleFinanzas.length > 0 && (
        <NavSection title="Finanzas" items={visibleFinanzas} />
      )}

      {/* Administración section (C-24) */}
      {visibleAdmin.length > 0 && (
        <NavSection title="Administración" items={visibleAdmin} />
      )}

      {/* Auditoría section (C-24) */}
      {visibleAuditoria.length > 0 && (
        <NavSection title="Auditoría" items={visibleAuditoria} />
      )}
    </nav>
  )
}
