/**
 * hooks/useAsignaciones.ts — TanStack Query hook for listing asignaciones.
 *
 * Used by the comision selector in GestionComisionPage.
 * Filters by PROFESOR or TUTOR roles for the authenticated user.
 */

import { useQuery } from '@tanstack/react-query'
import { listAsignaciones } from '../services/asignacionesService'

export const asignacionesKeys = {
  all: ['asignaciones'] as const,
  list: (userId?: string) =>
    [...asignacionesKeys.all, 'list', userId ?? 'all'] as const,
}

export function useAsignaciones(userId?: string) {
  return useQuery({
    queryKey: asignacionesKeys.list(userId),
    queryFn: () =>
      listAsignaciones(userId ? { usuario_id: userId } : undefined),
  })
}
