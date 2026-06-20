/**
 * hooks/useAprobacion.ts — TanStack Query hooks for comunicaciones approval queue.
 *
 * Hooks:
 *   useLotesPendientes — GET /api/comunicaciones?estado=Pendiente
 *   useAprobarLote     — POST /api/comunicaciones/aprobar
 *   useCancelarLote    — POST /api/comunicaciones/cancelar
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { aprobarLote, cancelarLote, getLotesPendientes } from '../services/aprobacionService'

export const aprobacionKeys = {
  all: ['coordinacion', 'aprobacion'] as const,
  pendientes: () => [...aprobacionKeys.all, 'pendientes'] as const,
}

// ---------------------------------------------------------------------------
// useLotesPendientes
// ---------------------------------------------------------------------------

export function useLotesPendientes() {
  return useQuery({
    queryKey: aprobacionKeys.pendientes(),
    queryFn: () => getLotesPendientes(),
  })
}

// ---------------------------------------------------------------------------
// useAprobarLote
// ---------------------------------------------------------------------------

export function useAprobarLote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (lote_id: string) => aprobarLote(lote_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: aprobacionKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useCancelarLote
// ---------------------------------------------------------------------------

export function useCancelarLote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (lote_id: string) => cancelarLote(lote_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: aprobacionKeys.all })
    },
  })
}
