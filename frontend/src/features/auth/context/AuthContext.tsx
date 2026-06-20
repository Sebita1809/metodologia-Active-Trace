import {
  createContext,
  useContext,
  useReducer,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { decodeJwt, isTokenExpired, type JwtClaims } from '@/shared/services/jwtDecode'
import { setAuthCallbacks } from '@/shared/services/api'

export interface AuthState {
  isAuthenticated: boolean
  claims: JwtClaims | null
}

type AuthAction =
  | { type: 'SET_SESSION'; payload: { accessToken: string; refreshToken: string } }
  | { type: 'CLEAR_SESSION' }

interface AuthContextValue extends AuthState {
  setSession: (accessToken: string, refreshToken: string) => void
  clearSession: () => void
}

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'SET_SESSION': {
      const claims = decodeJwt(action.payload.accessToken)
      if (!claims) return { isAuthenticated: false, claims: null }
      return { isAuthenticated: true, claims }
    }
    case 'CLEAR_SESSION':
      return { isAuthenticated: false, claims: null }
    default:
      return state
  }
}

/**
 * Compute the initial auth state synchronously from localStorage.
 * This prevents a flash of unauthenticated state on mount.
 */
function getInitialState(): AuthState {
  const accessToken = tokenStorage.getAccessToken()
  const refreshToken = tokenStorage.getRefreshToken()

  if (!accessToken) return { isAuthenticated: false, claims: null }

  const claims = decodeJwt(accessToken)
  if (!claims) {
    tokenStorage.clearTokens()
    return { isAuthenticated: false, claims: null }
  }

  if (isTokenExpired(claims)) {
    if (!refreshToken) {
      tokenStorage.clearTokens()
      return { isAuthenticated: false, claims: null }
    }
    // Token is expired but refresh exists — interceptor will handle it on first request
    return { isAuthenticated: true, claims }
  }

  return { isAuthenticated: true, claims }
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, undefined, getInitialState)

  const setSession = useCallback((accessToken: string, refreshToken: string) => {
    tokenStorage.setTokens(accessToken, refreshToken)
    dispatch({ type: 'SET_SESSION', payload: { accessToken, refreshToken } })
  }, [])

  const clearSession = useCallback(() => {
    tokenStorage.clearTokens()
    dispatch({ type: 'CLEAR_SESSION' })
  }, [])

  // Register the clearSession callback so the Axios interceptor can call it
  useEffect(() => {
    setAuthCallbacks({ onClearSession: clearSession })
  }, [clearSession])

  const value: AuthContextValue = {
    ...state,
    setSession,
    clearSession,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
