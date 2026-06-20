import { useMutation } from '@tanstack/react-query'
import { api } from '@/shared/services/api'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { useAuth } from '../context/AuthContext'

export function useLogout() {
  const { clearSession } = useAuth()

  return useMutation({
    mutationFn: async (): Promise<void> => {
      const refreshToken = tokenStorage.getRefreshToken()
      // Always clear locally first — even if network fails
      clearSession()
      if (refreshToken) {
        // Best-effort server-side revocation
        await api.post('/api/auth/logout', { refresh_token: refreshToken }).catch(() => {
          // Ignore network errors — session is already cleared locally
        })
      }
    },
  })
}
