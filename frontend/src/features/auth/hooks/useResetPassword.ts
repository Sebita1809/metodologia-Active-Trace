import { useMutation } from '@tanstack/react-query'
import { api } from '@/shared/services/api'

interface ResetPasswordInput {
  token: string
  password: string
}

export function useResetPassword() {
  return useMutation({
    mutationFn: async (data: ResetPasswordInput): Promise<void> => {
      await api.post('/api/auth/reset', data)
    },
  })
}
