/**
 * hooks/useAnalisis.ts — TanStack Query hooks for analisis endpoints.
 *
 * All hooks are disabled when asignacion_id is null (no comision selected).
 *
 * Hooks:
 *   useAtrasados    — GET /api/v1/analisis/atrasados
 *   useRanking      — GET /api/v1/analisis/ranking
 *   useNotasFinales — GET /api/v1/analisis/notas-finales
 *   useReporte      — GET /api/v1/analisis/reporte
 */

import { useQuery } from '@tanstack/react-query'
import {
  getAtrasados,
  getNotasFinales,
  getRanking,
  getReporte,
} from '../services/analisisService'

// Query key factories
export const analisisKeys = {
  all: ['analisis'] as const,
  atrasados: (asignacionId: string) =>
    [...analisisKeys.all, 'atrasados', asignacionId] as const,
  ranking: (asignacionId: string) =>
    [...analisisKeys.all, 'ranking', asignacionId] as const,
  notasFinales: (asignacionId: string) =>
    [...analisisKeys.all, 'notas-finales', asignacionId] as const,
  reporte: (asignacionId: string) =>
    [...analisisKeys.all, 'reporte', asignacionId] as const,
}

// ---------------------------------------------------------------------------
// useAtrasados
// ---------------------------------------------------------------------------

export function useAtrasados(asignacion_id: string | null) {
  return useQuery({
    queryKey: analisisKeys.atrasados(asignacion_id ?? ''),
    queryFn: () => getAtrasados(asignacion_id!),
    enabled: asignacion_id !== null,
  })
}

// ---------------------------------------------------------------------------
// useRanking
// ---------------------------------------------------------------------------

export function useRanking(asignacion_id: string | null) {
  return useQuery({
    queryKey: analisisKeys.ranking(asignacion_id ?? ''),
    queryFn: () => getRanking(asignacion_id!),
    enabled: asignacion_id !== null,
  })
}

// ---------------------------------------------------------------------------
// useNotasFinales
// ---------------------------------------------------------------------------

export function useNotasFinales(asignacion_id: string | null) {
  return useQuery({
    queryKey: analisisKeys.notasFinales(asignacion_id ?? ''),
    queryFn: () => getNotasFinales(asignacion_id!),
    enabled: asignacion_id !== null,
  })
}

// ---------------------------------------------------------------------------
// useReporte
// ---------------------------------------------------------------------------

export function useReporte(asignacion_id: string | null) {
  return useQuery({
    queryKey: analisisKeys.reporte(asignacion_id ?? ''),
    queryFn: () => getReporte(asignacion_id!),
    enabled: asignacion_id !== null,
  })
}
