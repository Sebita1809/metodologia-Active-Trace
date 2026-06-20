/**
 * services/aprobacionService.ts — API functions for comunicaciones approval queue.
 *
 * Paths confirmed by reading backend/app/api/v1/routers/comunicaciones.py:
 *   GET  /api/comunicaciones?estado=Pendiente — list pending lotes
 *   POST /api/comunicaciones/aprobar          — approve lote (by lote_id)
 *   POST /api/comunicaciones/cancelar         — cancel lote (by lote_id)
 *
 * NOTE: The design.md mentioned PUT /lotes/{id}/aprobar but the actual backend
 * uses POST /aprobar and POST /cancelar with lote_id in the body.
 *
 * No `any` allowed.
 */

import { api } from '@/shared/services/api'
import type {
  AprobacionResponse,
  AprobarLoteRequest,
  CancelacionResponse,
  CancelarLoteRequest,
  ComunicacionRead,
} from '../types'

const BASE = '/api/comunicaciones'

// ---------------------------------------------------------------------------
// GET /api/comunicaciones?estado=Pendiente — list pending lotes
// ---------------------------------------------------------------------------

export async function getLotesPendientes(): Promise<ComunicacionRead[]> {
  const { data } = await api.get<ComunicacionRead[]>(BASE, {
    params: { estado: 'Pendiente' },
  })
  return data
}

// ---------------------------------------------------------------------------
// POST /api/comunicaciones/aprobar — approve entire lote
// ---------------------------------------------------------------------------

export async function aprobarLote(
  lote_id: string,
): Promise<AprobacionResponse> {
  const body: AprobarLoteRequest = { lote_id }
  const { data } = await api.post<AprobacionResponse>(`${BASE}/aprobar`, body)
  return data
}

// ---------------------------------------------------------------------------
// POST /api/comunicaciones/cancelar — cancel entire lote
// ---------------------------------------------------------------------------

export async function cancelarLote(
  lote_id: string,
): Promise<CancelacionResponse> {
  const body: CancelarLoteRequest = { lote_id }
  const { data } = await api.post<CancelacionResponse>(`${BASE}/cancelar`, body)
  return data
}
