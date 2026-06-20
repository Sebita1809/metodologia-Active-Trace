import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mswServer'
import { api, setAuthCallbacks } from '../api'
import { tokenStorage } from '../tokenStorage'
import { makeFakeJwt } from '@/test/fixtures'

describe('api interceptors', () => {
  beforeEach(() => {
    tokenStorage.clearTokens()
    // Reset the isRefreshing flag by clearing module state between tests
    vi.restoreAllMocks()
  })

  afterEach(() => {
    tokenStorage.clearTokens()
  })

  it('injects Authorization header when access token exists', async () => {
    const jwt = makeFakeJwt({ roles: ['ADMIN'] })
    tokenStorage.setAccessToken(jwt)

    let capturedHeader: string | undefined

    server.use(
      http.get('http://localhost:8000/api/test', ({ request }) => {
        capturedHeader = request.headers.get('Authorization') ?? undefined
        return HttpResponse.json({ ok: true })
      }),
    )

    await api.get('/api/test')
    expect(capturedHeader).toBe(`Bearer ${jwt}`)
  })

  it('refreshes token transparently on 401 and retries original request', async () => {
    const oldAt = makeFakeJwt({ roles: ['ADMIN'] }, -1)
    const newAt = makeFakeJwt({ roles: ['ADMIN'] }, 3600)
    const rt = 'valid-refresh-token'

    tokenStorage.setTokens(oldAt, rt)

    let requestCount = 0

    server.use(
      http.get('http://localhost:8000/api/protected', () => {
        requestCount++
        if (requestCount === 1) {
          return new HttpResponse(null, { status: 401 })
        }
        return HttpResponse.json({ data: 'secret' })
      }),
      http.post('http://localhost:8000/api/auth/refresh', () => {
        return HttpResponse.json({
          access_token: newAt,
          refresh_token: 'new-rt',
        })
      }),
    )

    const response = await api.get('/api/protected')
    expect(response.data).toEqual({ data: 'secret' })
    expect(tokenStorage.getAccessToken()).toBe(newAt)
    expect(tokenStorage.getRefreshToken()).toBe('new-rt')
  })

  it('clears session and rejects when refresh fails', async () => {
    let sessionCleared = false
    setAuthCallbacks({ onClearSession: () => { sessionCleared = true } })

    const oldAt = makeFakeJwt({ roles: ['ADMIN'] }, -1)
    tokenStorage.setTokens(oldAt, 'bad-rt')

    server.use(
      http.get('http://localhost:8000/api/protected', () => {
        return new HttpResponse(null, { status: 401 })
      }),
      http.post('http://localhost:8000/api/auth/refresh', () => {
        return new HttpResponse(null, { status: 401 })
      }),
    )

    await expect(api.get('/api/protected')).rejects.toBeDefined()
    expect(sessionCleared).toBe(true)
  })

  it('does not trigger refresh on 403 — propagates as AccessDeniedError', async () => {
    let refreshCalled = false

    server.use(
      http.get('http://localhost:8000/api/admin', () => {
        return new HttpResponse(null, { status: 403 })
      }),
      http.post('http://localhost:8000/api/auth/refresh', () => {
        refreshCalled = true
        return HttpResponse.json({})
      }),
    )

    await expect(api.get('/api/admin')).rejects.toMatchObject({
      name: 'AccessDeniedError',
      status: 403,
    })
    expect(refreshCalled).toBe(false)
  })
})
