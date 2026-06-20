/**
 * services/comunicacionesService.ts — API functions for comunicaciones endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base path: /api/comunicaciones
 *
 * NOTE: The comunicaciones router is mounted at /api/comunicaciones in main.py.
 * If the prefix changes, update BASE here — it's the single source of truth.
 */

import { api } from '@/shared/services/api'
import type {
  ComunicacionRead,
  EncolarLoteRequest,
  EncolarLoteResponse,
  EstadoComunicacion,
  PreviewRequest,
  PreviewResponse,
} from '../types/comunicaciones'

export const COMUNICACIONES_BASE = '/api/comunicaciones'

// ---------------------------------------------------------------------------
// POST /api/comunicaciones/preview
// Render template without persisting (RN-16)
// ---------------------------------------------------------------------------

export async function previewComunicacion(
  body: PreviewRequest,
): Promise<PreviewResponse> {
  const { data } = await api.post<PreviewResponse>(
    `${COMUNICACIONES_BASE}/preview`,
    body,
  )
  return data
}

// ---------------------------------------------------------------------------
// POST /api/comunicaciones/
// Encolar lote — returns lote_id
// ---------------------------------------------------------------------------

export async function encolarLote(
  body: EncolarLoteRequest,
): Promise<EncolarLoteResponse> {
  const { data } = await api.post<EncolarLoteResponse>(COMUNICACIONES_BASE, body)
  return data
}

// ---------------------------------------------------------------------------
// GET /api/comunicaciones/?lote_id=...&estado=...
// List queue — filter by lote_id and/or estado
// ---------------------------------------------------------------------------

export async function listCola(params: {
  lote_id?: string
  estado?: EstadoComunicacion
}): Promise<ComunicacionRead[]> {
  const { data } = await api.get<ComunicacionRead[]>(COMUNICACIONES_BASE, {
    params,
  })
  return data
}
