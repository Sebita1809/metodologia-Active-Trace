import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { AuthProvider, useAuth } from '../context/AuthContext'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { makeFakeJwt, makeExpiredJwt } from '@/test/fixtures'

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    )
  }
}

describe('AuthContext', () => {
  beforeEach(() => {
    tokenStorage.clearTokens()
  })

  afterEach(() => {
    tokenStorage.clearTokens()
  })

  it('starts unauthenticated with no stored tokens', () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: makeWrapper(),
    })
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.claims).toBeNull()
  })

  it('hydrates session from localStorage with valid token', () => {
    const jwt = makeFakeJwt({ roles: ['ADMIN'] })
    tokenStorage.setTokens(jwt, 'rt-value')

    const { result } = renderHook(() => useAuth(), {
      wrapper: makeWrapper(),
    })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.claims?.roles).toContain('ADMIN')
  })

  it('does not authenticate with expired token and no refresh token', () => {
    const expiredJwt = makeExpiredJwt(['TUTOR'])
    tokenStorage.setAccessToken(expiredJwt)
    // No refresh token stored

    const { result } = renderHook(() => useAuth(), {
      wrapper: makeWrapper(),
    })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.claims).toBeNull()
  })

  it('setSession stores tokens and updates state', () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: makeWrapper(),
    })

    const jwt = makeFakeJwt({ roles: ['COORDINADOR'] })

    act(() => {
      result.current.setSession(jwt, 'new-rt')
    })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.claims?.roles).toContain('COORDINADOR')
    expect(tokenStorage.getAccessToken()).toBe(jwt)
  })

  it('clearSession removes tokens and resets state', () => {
    const jwt = makeFakeJwt({ roles: ['ADMIN'] })

    const { result } = renderHook(() => useAuth(), {
      wrapper: makeWrapper(),
    })

    act(() => {
      result.current.setSession(jwt, 'rt-value')
    })

    act(() => {
      result.current.clearSession()
    })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.claims).toBeNull()
    expect(tokenStorage.getAccessToken()).toBeNull()
    expect(tokenStorage.getRefreshToken()).toBeNull()
  })
})
