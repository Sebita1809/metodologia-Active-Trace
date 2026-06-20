/**
 * hooks/useColoquios.ts — TanStack Query hooks for coloquios endpoints.
 *
 * Hooks:
 *   useEvaluaciones      — GET /api/v1/coloquios
 *   useCreateEvaluacion  — POST /api/v1/coloquios
 *   useImportarAlumnos   — POST /api/v1/coloquios/{id}/alumnos
 *   useReservas          — GET /api/v1/coloquios/{id}/reservas
 *   useResultados        — GET /api/v1/coloquios/{id}/resultados
 *   useMetricasColoquios — GET /api/v1/coloquios/metricas
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createEvaluacion,
  getEvaluaciones,
  getMetricas,
  getReservas,
  getResultados,
  importarAlumnos,
} from '../services/coloquiosService'
import type { CrearEvaluacionRequest } from '../types'

export const coloquiosKeys = {
  all: ['coordinacion', 'coloquios'] as const,
  list: () => [...coloquiosKeys.all, 'list'] as const,
  metricas: () => [...coloquiosKeys.all, 'metricas'] as const,
  reservas: (evaluacionId: string) =>
    [...coloquiosKeys.all, 'reservas', evaluacionId] as const,
  resultados: (evaluacionId: string) =>
    [...coloquiosKeys.all, 'resultados', evaluacionId] as const,
}

// ---------------------------------------------------------------------------
// useEvaluaciones
// ---------------------------------------------------------------------------

export function useEvaluaciones() {
  return useQuery({
    queryKey: coloquiosKeys.list(),
    queryFn: () => getEvaluaciones(),
  })
}

// ---------------------------------------------------------------------------
// useCreateEvaluacion
// ---------------------------------------------------------------------------

export function useCreateEvaluacion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CrearEvaluacionRequest) => createEvaluacion(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: coloquiosKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useImportarAlumnos
// ---------------------------------------------------------------------------

export function useImportarAlumnos() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ evaluacionId, file }: { evaluacionId: string; file: File }) =>
      importarAlumnos(evaluacionId, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: coloquiosKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useReservas
// ---------------------------------------------------------------------------

export function useReservas(evaluacionId: string | null) {
  return useQuery({
    queryKey: coloquiosKeys.reservas(evaluacionId ?? ''),
    queryFn: () => getReservas(evaluacionId!),
    enabled: evaluacionId !== null,
  })
}

// ---------------------------------------------------------------------------
// useResultados
// ---------------------------------------------------------------------------

export function useResultados(evaluacionId: string | null) {
  return useQuery({
    queryKey: coloquiosKeys.resultados(evaluacionId ?? ''),
    queryFn: () => getResultados(evaluacionId!),
    enabled: evaluacionId !== null,
  })
}

// ---------------------------------------------------------------------------
// useMetricasColoquios
// ---------------------------------------------------------------------------

export function useMetricasColoquios() {
  return useQuery({
    queryKey: coloquiosKeys.metricas(),
    queryFn: () => getMetricas(),
  })
}
