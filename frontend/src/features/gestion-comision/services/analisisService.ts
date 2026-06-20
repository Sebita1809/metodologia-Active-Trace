/**
 * services/analisisService.ts — API functions for analisis endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base path: /api/v1/analisis
 */

import { api } from '@/shared/services/api'
import type {
  AtrasadosResponse,
  NotasFinalesResponse,
  RankingResponse,
  ReporteAsignacion,
} from '../types/analisis'

const BASE = '/api/v1/analisis'

// ---------------------------------------------------------------------------
// GET /api/v1/analisis/atrasados?asignacion_id=...
// ---------------------------------------------------------------------------

export async function getAtrasados(asignacion_id: string): Promise<AtrasadosResponse> {
  const { data } = await api.get<AtrasadosResponse>(`${BASE}/atrasados`, {
    params: { asignacion_id },
  })
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/analisis/ranking?asignacion_id=...
// ---------------------------------------------------------------------------

export async function getRanking(asignacion_id: string): Promise<RankingResponse> {
  const { data } = await api.get<RankingResponse>(`${BASE}/ranking`, {
    params: { asignacion_id },
  })
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/analisis/notas-finales?asignacion_id=...
// Optional: fecha_desde, fecha_hasta for COORDINADOR/ADMIN date range filter (C-23 F2.9)
// ---------------------------------------------------------------------------

export async function getNotasFinales(
  asignacion_id: string,
  dateRange?: { fecha_desde?: string; fecha_hasta?: string },
): Promise<NotasFinalesResponse> {
  const { data } = await api.get<NotasFinalesResponse>(`${BASE}/notas-finales`, {
    params: { asignacion_id, ...dateRange },
  })
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/analisis/reporte?asignacion_id=...
// ---------------------------------------------------------------------------

export async function getReporte(asignacion_id: string): Promise<ReporteAsignacion> {
  const { data } = await api.get<ReporteAsignacion>(`${BASE}/reporte`, {
    params: { asignacion_id },
  })
  return data
}
