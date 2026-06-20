/**
 * hooks/useMonitorSeguimiento.ts — Wrapper hook for monitor de seguimiento.
 *
 * Combines useNotasFinales + useReporte and adds optional date range parameters
 * (fecha_desde / fecha_hasta) for COORDINADOR/ADMIN roles.
 *
 * This is an extension of C-23 (F2.9).
 */

import { useQuery } from '@tanstack/react-query'
import { getNotasFinales, getReporte } from '../services/analisisService'

export interface MonitorSeguimientoFilters {
  fecha_desde?: string
  fecha_hasta?: string
}

export const monitorSeguimientoKeys = {
  all: ['monitor-seguimiento'] as const,
  notasFinales: (asignacionId: string, filters?: MonitorSeguimientoFilters) =>
    [...monitorSeguimientoKeys.all, 'notas-finales', asignacionId, filters ?? {}] as const,
  reporte: (asignacionId: string) =>
    [...monitorSeguimientoKeys.all, 'reporte', asignacionId] as const,
}

export function useMonitorSeguimiento(
  asignacion_id: string | null,
  filters?: MonitorSeguimientoFilters,
) {
  const notasQuery = useQuery({
    queryKey: monitorSeguimientoKeys.notasFinales(asignacion_id ?? '', filters),
    queryFn: () =>
      getNotasFinales(asignacion_id!, filters),
    enabled: asignacion_id !== null,
  })

  const reporteQuery = useQuery({
    queryKey: monitorSeguimientoKeys.reporte(asignacion_id ?? ''),
    queryFn: () => getReporte(asignacion_id!),
    enabled: asignacion_id !== null,
  })

  return {
    notasQuery,
    reporteQuery,
    isLoading: notasQuery.isLoading || reporteQuery.isLoading,
    items: notasQuery.data?.items ?? [],
    tieneDatos: reporteQuery.data?.tiene_datos ?? false,
  }
}
