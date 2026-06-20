import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { screen, render } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { RequireAuth } from '../RequireAuth'
import { RequireRole } from '../RequireRole'
import { AuthProvider } from '@/features/auth/context/AuthContext'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { makeFakeJwt } from '@/test/fixtures'

function renderInAuth(
  ui: ReactNode,
  initialEntries: string[] = ['/'],
) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('RequireAuth', () => {
  beforeEach(() => tokenStorage.clearTokens())
  afterEach(() => tokenStorage.clearTokens())

  it('redirects to /login when not authenticated', () => {
    renderInAuth(
      <Routes>
        <Route
          path="/protected"
          element={
            <RequireAuth>
              <div>Protected content</div>
            </RequireAuth>
          }
        />
        <Route path="/login" element={<div>Login page</div>} />
      </Routes>,
      ['/protected'],
    )

    expect(screen.getByText('Login page')).toBeInTheDocument()
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument()
  })

  it('renders children when authenticated', () => {
    const jwt = makeFakeJwt({ roles: ['ADMIN'] })
    tokenStorage.setTokens(jwt, 'rt')

    renderInAuth(
      <Routes>
        <Route
          path="/protected"
          element={
            <RequireAuth>
              <div>Protected content</div>
            </RequireAuth>
          }
        />
        <Route path="/login" element={<div>Login page</div>} />
      </Routes>,
      ['/protected'],
    )

    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })

  it('preserves the original location in state when redirecting', () => {
    renderInAuth(
      <Routes>
        <Route
          path="/dashboard/settings"
          element={
            <RequireAuth>
              <div>Settings</div>
            </RequireAuth>
          }
        />
        <Route
          path="/login"
          element={<div data-testid="login">Login page</div>}
        />
      </Routes>,
      ['/dashboard/settings'],
    )

    expect(screen.getByTestId('login')).toBeInTheDocument()
    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
  })
})

describe('RequireRole', () => {
  beforeEach(() => tokenStorage.clearTokens())
  afterEach(() => tokenStorage.clearTokens())

  it('renders children when user has the required role', () => {
    const jwt = makeFakeJwt({ roles: ['ADMIN'] })
    tokenStorage.setTokens(jwt, 'rt')

    renderInAuth(
      <Routes>
        <Route
          path="/"
          element={
            <RequireAuth>
              <RequireRole roles={['ADMIN']}>
                <div>Admin content</div>
              </RequireRole>
            </RequireAuth>
          }
        />
        <Route path="/login" element={<div>Login</div>} />
      </Routes>,
    )

    expect(screen.getByText('Admin content')).toBeInTheDocument()
  })

  it('shows access denied when user lacks the required role', () => {
    const jwt = makeFakeJwt({ roles: ['ALUMNO'] })
    tokenStorage.setTokens(jwt, 'rt')

    renderInAuth(
      <Routes>
        <Route
          path="/"
          element={
            <RequireAuth>
              <RequireRole roles={['ADMIN', 'COORDINADOR']}>
                <div>Admin content</div>
              </RequireRole>
            </RequireAuth>
          }
        />
        <Route path="/login" element={<div>Login</div>} />
      </Routes>,
    )

    expect(screen.getByText(/Acceso denegado/i)).toBeInTheDocument()
    expect(screen.queryByText('Admin content')).not.toBeInTheDocument()
  })
})
