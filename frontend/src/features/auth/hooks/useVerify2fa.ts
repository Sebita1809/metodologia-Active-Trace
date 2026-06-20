import { useMutation } from '@tanstack/react-query'
import { api } from '@/shared/services/api'
import type { TwoFactorResponse } from '../types'

interface Verify2faInput {
  partial_token: string
  code: string
}

export function useVerify2fa() {
  return useMutation({
    mutationFn: async (data: Verify2faInput): Promise<TwoFactorResponse> => {
      const response = await api.post<TwoFactorResponse>(
        '/api/auth/2fa/login-verify',
        data,
      )
      return response.data
    },
  })
}
