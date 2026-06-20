import { useMutation } from '@tanstack/react-query'
import { api } from '@/shared/services/api'
import { tokenStorage } from '@/shared/services/tokenStorage'
import type { LoginFormData, LoginResponse } from '../types'

async function resolveTenant(slug: string): Promise<string> {
  const { data } = await api.get<{ id: string; nombre: string }>(
    `/api/auth/tenant/${encodeURIComponent(slug)}`,
  )
  return data.id
}

export function useLogin() {
  return useMutation({
    mutationFn: async (data: LoginFormData): Promise<LoginResponse> => {
      const tenantId = await resolveTenant(data.tenant)
      tokenStorage.setTenantId(tenantId)

      const response = await api.post<LoginResponse>(
        '/api/auth/login',
        { email: data.email, password: data.password },
        { headers: { 'X-Tenant-ID': tenantId } },
      )
      return response.data
    },
  })
}
