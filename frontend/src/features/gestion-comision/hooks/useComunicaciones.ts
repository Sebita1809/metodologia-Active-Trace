/**
 * hooks/useComunicaciones.ts — TanStack Query hooks for comunicaciones endpoints.
 *
 * Hooks:
 *   usePreviewComunicacion  — mutation: POST /preview (no persist)
 *   useEnviarComunicacion   — mutation: POST / (encolar lote → lote_id)
 *   useColaComunicaciones   — query: GET / by lote_id, with conditional polling
 *
 * Polling strategy (design decision 4):
 *   - refetchInterval active while at least one message is in a non-terminal state
 *   - Stops automatically when all messages reach terminal state (Enviado/Error/Cancelado)
 *   - Default interval: POLL_INTERVAL_MS (3 s), configurable per call
 */

import { useMutation, useQuery } from '@tanstack/react-query'
import {
  encolarLote,
  listCola,
  previewComunicacion,
} from '../services/comunicacionesService'
import type { EncolarLoteRequest, PreviewRequest } from '../types/comunicaciones'
import { isEstadoTerminal } from '../types/comunicaciones'

export const POLL_INTERVAL_MS = 3_000

// Query key factories
export const comunicacionesKeys = {
  all: ['comunicaciones'] as const,
  cola: (lote_id: string) =>
    [...comunicacionesKeys.all, 'cola', lote_id] as const,
}

// ---------------------------------------------------------------------------
// usePreviewComunicacion — POST /preview (no side effects)
// ---------------------------------------------------------------------------

export function usePreviewComunicacion() {
  return useMutation({
    mutationFn: (body: PreviewRequest) => previewComunicacion(body),
  })
}

// ---------------------------------------------------------------------------
// useEnviarComunicacion — POST / (encolar lote)
// ---------------------------------------------------------------------------

export function useEnviarComunicacion() {
  return useMutation({
    mutationFn: (body: EncolarLoteRequest) => encolarLote(body),
  })
}

// ---------------------------------------------------------------------------
// useColaComunicaciones — GET / by lote_id with conditional polling
// ---------------------------------------------------------------------------

export function useColaComunicaciones(
  lote_id: string | null,
  pollIntervalMs = POLL_INTERVAL_MS,
) {
  return useQuery({
    queryKey: comunicacionesKeys.cola(lote_id ?? ''),
    queryFn: () => listCola({ lote_id: lote_id! }),
    enabled: lote_id !== null,
    refetchInterval: (query) => {
      const messages = query.state.data
      if (!messages || messages.length === 0) return false

      // Stop polling when all messages are in a terminal state
      const allTerminal = messages.every((m) => isEstadoTerminal(m.estado))
      return allTerminal ? false : pollIntervalMs
    },
  })
}
