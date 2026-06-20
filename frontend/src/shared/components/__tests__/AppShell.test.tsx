import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { screen, render } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { AppShell } from '../AppShell'
import { AuthProvider } from '@/features/auth/context/AuthContext'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { makeFakeJwt } from '@/test/fixtures'
import type { Role } from '@/shared/services/jwtDecode'

function renderAppShell(roles: Role[], sub = 'user@example.com') {
  const jwt = makeFakeJwt({ sub, roles })
  tokenStorage.setTokens(jwt, 'rt')

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <Routes>
            <Route path="/dashboard" element={<AppShell />}>
              <Route index element={<div>Dashboard content</div>} />
            </Route>
            <Route path="/login" element={<div>Login page</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function renderOutsideShell(children: ReactNode) {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<>{children}</>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AppShell', () => {
  beforeEach(() => tokenStorage.clearTokens())
  afterEach(() => tokenStorage.clearTokens())

  it('renders user identity and logout button', () => {
    renderAppShell(['ADMIN'])
    expect(screen.getAllByText('user@example.com').length).toBeGreaterThan(0)
    expect(screen.getByText('Cerrar sesión')).toBeInTheDocument()
  })

  it('shows Dashboard nav item for all roles', () => {
    renderAppShell(['ALUMNO'])
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('hides Finanzas menu item for non-finance roles', () => {
    renderAppShell(['ALUMNO'])
    expect(screen.queryByText('Finanzas')).not.toBeInTheDocument()
  })

  it('shows Finanzas menu item for FINANZAS role', () => {
    renderAppShell(['FINANZAS'])
    expect(screen.getByText('Finanzas')).toBeInTheDocument()
  })

  it('shows Alumnos menu item for TUTOR role', () => {
    renderAppShell(['TUTOR'])
    expect(screen.getByText('Alumnos')).toBeInTheDocument()
  })

  it('auth pages render without shell (no logout button)', () => {
    renderOutsideShell(<div>Login standalone</div>)
    expect(screen.getByText('Login standalone')).toBeInTheDocument()
    expect(screen.queryByText('Cerrar sesión')).not.toBeInTheDocument()
  })
})
