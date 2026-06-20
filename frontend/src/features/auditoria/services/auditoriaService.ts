/**
 * services/auditoriaService.ts — API functions for auditoría endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base path: /api/auditoria
 *
 * Panel endpoints (C-19):
 *   GET /api/auditoria/panel/acciones-por-dia
 *   GET /api/auditoria/panel/comunicaciones-por-docente
 *   GET /api/auditoria/panel/interacciones-docente-materia
 *   GET /api/auditoria/panel/ultimas-acciones
 *   GET /api/auditoria/log
 *
 * Scope is derived from the JWT — COORDINADOR sees their team; ADMIN sees all.
 */

import { api } from '@/shared/services/api'
import type {
  AccionesPorDiaResponse,
  ComunicacionesPorDocenteResponse,
  InteraccionesDocenteMateriaResponse,
  UltimasAccionesResponse,
  LogFiltradoResponse,
  AuditoriaFilters,
  AccionesPorDiaFilters,
} from '../types'

const BASE = '/api/auditoria'

// ---------------------------------------------------------------------------
// GET /api/auditoria/panel/acciones-por-dia
// ---------------------------------------------------------------------------

export async function getAccionesPorDia(
  filters: AccionesPorDiaFilters,
): Promise<AccionesPorDiaResponse> {
  const { data } = await api.get<AccionesPorDiaResponse>(
    `${BASE}/panel/acciones-por-dia`,
    {
      params: {
        desde: filters.desde,
        hasta: filters.hasta,
      },
    },
  )
  return data
}

// ---------------------------------------------------------------------------
// GET /api/auditoria/panel/comunicaciones-por-docente
// ---------------------------------------------------------------------------

export async function getComunicacionesPorDocente(): Promise<ComunicacionesPorDocenteResponse> {
  const { data } = await api.get<ComunicacionesPorDocenteResponse>(
    `${BASE}/panel/comunicaciones-por-docente`,
  )
  return data
}

// ---------------------------------------------------------------------------
// GET /api/auditoria/panel/interacciones-docente-materia
// ---------------------------------------------------------------------------

export async function getInteraccionesDocente(): Promise<InteraccionesDocenteMateriaResponse> {
  const { data } = await api.get<InteraccionesDocenteMateriaResponse>(
    `${BASE}/panel/interacciones-docente-materia`,
  )
  return data
}

// ---------------------------------------------------------------------------
// GET /api/auditoria/panel/ultimas-acciones
// ---------------------------------------------------------------------------

export async function getUltimasAcciones(
  limit: number = 200,
): Promise<UltimasAccionesResponse> {
  const { data } = await api.get<UltimasAccionesResponse>(
    `${BASE}/panel/ultimas-acciones`,
    {
      params: { limit },
    },
  )
  return data
}

// ---------------------------------------------------------------------------
// GET /api/auditoria/log — filtered paginated log
// ---------------------------------------------------------------------------

export async function getLogCompleto(
  filters: AuditoriaFilters = {},
): Promise<LogFiltradoResponse> {
  const { data } = await api.get<LogFiltradoResponse>(`${BASE}/log`, {
    params: {
      ...(filters.desde ? { desde: filters.desde } : {}),
      ...(filters.hasta ? { hasta: filters.hasta } : {}),
      ...(filters.materia_id ? { materia_id: filters.materia_id } : {}),
      ...(filters.usuario_id ? { usuario_id: filters.usuario_id } : {}),
      ...(filters.accion ? { accion: filters.accion } : {}),
      ...(filters.estado ? { estado: filters.estado } : {}),
      limit: filters.limit ?? 100,
      offset: filters.offset ?? 0,
    },
  })
  return data
}
