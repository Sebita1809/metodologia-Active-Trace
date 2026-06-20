/**
 * hooks/useEncuentros.ts — TanStack Query hooks for encuentros and guardias endpoints.
 *
 * Hooks:
 *   useEncuentrosTenant  — GET /api/v1/admin/encuentros
 *   useGuardias          — GET /api/v1/guardias
 *   useCreateGuardia     — POST /api/v1/guardias
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getEncuentrosTenant } from '../services/encuentrosService'
import { createGuardia, getGuardias } from '../services/guardiasService'
import type { EncuentroFilters, GuardiaFilters, RegistrarGuardiaRequest } from '../types'

export const encuentrosKeys = {
  all: ['coordinacion', 'encuentros'] as const,
  tenant: (filters?: EncuentroFilters) =>
    [...encuentrosKeys.all, 'tenant', filters ?? {}] as const,
}

export const guardiasKeys = {
  all: ['coordinacion', 'guardias'] as const,
  list: (filters?: GuardiaFilters) =>
    [...guardiasKeys.all, 'list', filters ?? {}] as const,
}

// ---------------------------------------------------------------------------
// useEncuentrosTenant
// ---------------------------------------------------------------------------

export function useEncuentrosTenant(filters?: EncuentroFilters) {
  return useQuery({
    queryKey: encuentrosKeys.tenant(filters),
    queryFn: () => getEncuentrosTenant(filters),
  })
}

// ---------------------------------------------------------------------------
// useGuardias
// ---------------------------------------------------------------------------

export function useGuardias(filters?: GuardiaFilters) {
  return useQuery({
    queryKey: guardiasKeys.list(filters),
    queryFn: () => getGuardias(filters),
  })
}

// ---------------------------------------------------------------------------
// useCreateGuardia
// ---------------------------------------------------------------------------

export function useCreateGuardia() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: RegistrarGuardiaRequest) => createGuardia(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: guardiasKeys.all })
    },
  })
}
