import axios, {
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import { tokenStorage } from './tokenStorage'

// Typed API errors — plain objects instead of class declarations (erasableSyntaxOnly)
export interface ApiError {
  name: string
  status: number
  code: string
  message: string
}

export function makeApiError(status: number, code: string, message: string): ApiError {
  return { name: 'ApiError', status, code, message }
}

export function makeAccessDeniedError(message = 'Access denied'): ApiError {
  return { name: 'AccessDeniedError', status: 403, code: 'ACCESS_DENIED', message }
}

export function makeServerError(status: number, message = 'Server error'): ApiError {
  return { name: 'ServerError', status, code: 'SERVER_ERROR', message }
}

export function isAccessDeniedError(err: unknown): err is ApiError {
  return (
    typeof err === 'object' &&
    err !== null &&
    (err as ApiError).name === 'AccessDeniedError'
  )
}

// Callback holder — set by AuthProvider so api.ts (non-React) can clear the session
let onClearSession: (() => void) | null = null

export function setAuthCallbacks(callbacks: { onClearSession: () => void }) {
  onClearSession = callbacks.onClearSession
}

// Queue of pending resolvers waiting for a token refresh
type PendingResolver = (token: string | null) => void
let isRefreshing = false
let pendingRequests: PendingResolver[] = []

function resolvePending(token: string | null) {
  pendingRequests.forEach((resolve) => resolve(token))
  pendingRequests = []
}

// Axios instance
export const api: AxiosInstance = axios.create({
  baseURL: (import.meta.env['VITE_API_BASE_URL'] as string | undefined) ?? '',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor — inject Authorization + X-Tenant-ID headers
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccessToken()
  if (token && config.headers) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  const tenantId = tokenStorage.getTenantId()
  if (tenantId && config.headers) {
    config.headers['X-Tenant-ID'] = tenantId
  }
  return config
})

// Response interceptor — handle 401, 403, 5xx
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) {
      return Promise.reject(makeServerError(0, 'Network error'))
    }

    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }
    const status = error.response?.status

    // 403 — access denied, do NOT refresh, propagate as typed error
    if (status === 403) {
      return Promise.reject(makeAccessDeniedError())
    }

    // 5xx — propagate as typed error
    if (status !== undefined && status >= 500) {
      return Promise.reject(makeServerError(status))
    }

    // 401 on /api/auth/refresh itself — session is dead
    if (
      status === 401 &&
      originalRequest.url?.includes('/api/auth/refresh')
    ) {
      isRefreshing = false
      resolvePending(null)
      onClearSession?.()
      return Promise.reject(error)
    }

    // 401 on any other request — attempt a single refresh
    if (status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Queue this request until refresh completes
        return new Promise((resolve, reject) => {
          pendingRequests.push((token) => {
            if (!token) {
              reject(error)
              return
            }
            if (originalRequest.headers) {
              originalRequest.headers['Authorization'] = `Bearer ${token}`
            }
            resolve(api(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshToken = tokenStorage.getRefreshToken()
        if (!refreshToken) throw new Error('No refresh token')

        const { data } = await api.post<{
          access_token: string
          refresh_token: string
        }>('/api/auth/refresh', { refresh_token: refreshToken })

        tokenStorage.setTokens(data.access_token, data.refresh_token)
        isRefreshing = false
        resolvePending(data.access_token)

        if (originalRequest.headers) {
          originalRequest.headers['Authorization'] = `Bearer ${data.access_token}`
        }
        return api(originalRequest)
      } catch {
        isRefreshing = false
        resolvePending(null)
        onClearSession?.()
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)
