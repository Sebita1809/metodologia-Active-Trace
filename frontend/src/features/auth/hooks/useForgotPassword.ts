import { useMutation } from '@tanstack/react-query'
import { api } from '@/shared/services/api'

export function useForgotPassword() {
  return useMutation({
    mutationFn: async (email: string): Promise<void> => {
      await api.post('/api/auth/forgot', { email })
    },
  })
}
