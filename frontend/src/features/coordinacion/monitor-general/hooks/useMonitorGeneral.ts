/**
 * hooks/useMonitorGeneral.ts — TanStack Query hook for monitor general endpoint.
 *
 * Hook:
 *   useMonitorGeneral — GET /api/v1/calificaciones/monitor
 */

import { useQuery } from '@tanstack/react-query'
import { getMonitorGeneral } from '../services/monitorGeneralService'
import type { MonitorGeneralFilters } from '../types'

export const monitorGeneralKeys = {
  all: ['coordinacion', 'monitor-general'] as const,
  list: (filters?: MonitorGeneralFilters) =>
    [...monitorGeneralKeys.all, 'list', filters ?? {}] as const,
}

export function useMonitorGeneral(filters?: MonitorGeneralFilters) {
  return useQuery({
    queryKey: monitorGeneralKeys.list(filters),
    queryFn: () => getMonitorGeneral(filters),
  })
}
