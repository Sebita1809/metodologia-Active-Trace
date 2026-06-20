/**
 * hooks/useAuditoria.ts — TanStack Query hooks for auditoría endpoints.
 */

import { useQuery } from '@tanstack/react-query'
import {
  getAccionesPorDia,
  getComunicacionesPorDocente,
  getInteraccionesDocente,
  getLogCompleto,
  getUltimasAcciones,
} from '../services/auditoriaService'
import type { AccionesPorDiaFilters, AuditoriaFilters } from '../types'

// Query key factories
export const auditoriaKeys = {
  all: ['auditoria'] as const,
  panel: () => [...auditoriaKeys.all, 'panel'] as const,
  accionesPorDia: (filters: AccionesPorDiaFilters) =>
    [...auditoriaKeys.panel(), 'acciones-por-dia', filters] as const,
  comunicacionesPorDocente: () =>
    [...auditoriaKeys.panel(), 'comunicaciones-por-docente'] as const,
  interaccionesDocente: () =>
    [...auditoriaKeys.panel(), 'interacciones-docente'] as const,
  ultimasAcciones: (limit: number) =>
    [...auditoriaKeys.panel(), 'ultimas-acciones', limit] as const,
  logCompleto: (filters: AuditoriaFilters) =>
    [...auditoriaKeys.all, 'log', filters] as const,
}

// ---------------------------------------------------------------------------
// useAccionesPorDia — GET /api/auditoria/panel/acciones-por-dia
// ---------------------------------------------------------------------------

export function useAccionesPorDia(filters: AccionesPorDiaFilters | null) {
  return useQuery({
    queryKey: auditoriaKeys.accionesPorDia(
      filters ?? { desde: '', hasta: '' },
    ),
    queryFn: () => getAccionesPorDia(filters!),
    enabled: filters !== null && filters.desde !== '' && filters.hasta !== '',
  })
}

// ---------------------------------------------------------------------------
// useComunicacionesPorDocente — GET /api/auditoria/panel/comunicaciones-por-docente
// ---------------------------------------------------------------------------

export function useComunicacionesPorDocente() {
  return useQuery({
    queryKey: auditoriaKeys.comunicacionesPorDocente(),
    queryFn: getComunicacionesPorDocente,
  })
}

// ---------------------------------------------------------------------------
// useInteraccionesDocente — GET /api/auditoria/panel/interacciones-docente-materia
// ---------------------------------------------------------------------------

export function useInteraccionesDocente() {
  return useQuery({
    queryKey: auditoriaKeys.interaccionesDocente(),
    queryFn: getInteraccionesDocente,
  })
}

// ---------------------------------------------------------------------------
// useUltimasAcciones — GET /api/auditoria/panel/ultimas-acciones
// ---------------------------------------------------------------------------

export function useUltimasAcciones(limit: number = 200) {
  return useQuery({
    queryKey: auditoriaKeys.ultimasAcciones(limit),
    queryFn: () => getUltimasAcciones(limit),
  })
}

// ---------------------------------------------------------------------------
// useAuditoriaPanel — alias hook that fetches all panel sub-sections
// Deprecated: use individual hooks for fine-grained control
// ---------------------------------------------------------------------------

export function useAuditoriaPanel(filters: AccionesPorDiaFilters | null) {
  return useAccionesPorDia(filters)
}

// ---------------------------------------------------------------------------
// useLogCompleto — GET /api/auditoria/log (ADMIN only)
// ---------------------------------------------------------------------------

export function useLogCompleto(filters: AuditoriaFilters = {}) {
  return useQuery({
    queryKey: auditoriaKeys.logCompleto(filters),
    queryFn: () => getLogCompleto(filters),
  })
}
