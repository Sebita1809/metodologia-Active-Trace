/**
 * hooks/useLiquidaciones.ts — TanStack Query hooks for liquidaciones endpoints.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  calcularPeriodo,
  cerrarLiquidacion,
  exportarLiquidacionCSV,
  getHistorial,
  getLiquidaciones,
} from '../services/liquidacionesService'
import type { LiquidacionFilters, CerrarLiquidacionRequest, CalcularLiquidacionRequest } from '../types'

// Query key factories
export const liquidacionesKeys = {
  all: ['liquidaciones'] as const,
  periodo: (filters: LiquidacionFilters) =>
    [...liquidacionesKeys.all, 'periodo', filters] as const,
  historial: () => [...liquidacionesKeys.all, 'historial'] as const,
}

// ---------------------------------------------------------------------------
// useLiquidaciones — query for GET /periodo
// ---------------------------------------------------------------------------

export function useLiquidaciones(filters: LiquidacionFilters | null) {
  return useQuery({
    queryKey: liquidacionesKeys.periodo(filters ?? { cohorte_id: '', mes: 0, anio: 0 }),
    queryFn: () => getLiquidaciones(filters!),
    enabled:
      filters !== null &&
      filters.cohorte_id !== '' &&
      filters.mes > 0 &&
      filters.anio > 0,
  })
}

// ---------------------------------------------------------------------------
// useHistorialLiquidaciones — query for GET /historial
// ---------------------------------------------------------------------------

export function useHistorialLiquidaciones() {
  return useQuery({
    queryKey: liquidacionesKeys.historial(),
    queryFn: getHistorial,
  })
}

// ---------------------------------------------------------------------------
// useCalcularLiquidacion — mutation for POST /calcular
// ---------------------------------------------------------------------------

export function useCalcularLiquidacion(currentFilters: LiquidacionFilters | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CalcularLiquidacionRequest) => calcularPeriodo(data),
    onSuccess: () => {
      if (currentFilters) {
        void queryClient.invalidateQueries({
          queryKey: liquidacionesKeys.periodo(currentFilters),
        })
      }
    },
  })
}

// ---------------------------------------------------------------------------
// useCerrarLiquidacion — mutation for POST /cerrar (irreversible RN-22)
// ---------------------------------------------------------------------------

export function useCerrarLiquidacion(currentFilters: LiquidacionFilters | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CerrarLiquidacionRequest) => cerrarLiquidacion(data),
    onSuccess: () => {
      // Invalidate both periodo and historial
      if (currentFilters) {
        void queryClient.invalidateQueries({
          queryKey: liquidacionesKeys.periodo(currentFilters),
        })
      }
      void queryClient.invalidateQueries({
        queryKey: liquidacionesKeys.historial(),
      })
    },
  })
}

// ---------------------------------------------------------------------------
// useExportarLiquidacion — mutation for CSV export
// ---------------------------------------------------------------------------

export function useExportarLiquidacion() {
  return useMutation({
    mutationFn: (filters: LiquidacionFilters) => exportarLiquidacionCSV(filters),
  })
}
