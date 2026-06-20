/**
 * services/asignacionesService.ts — API functions for asignaciones and equipo endpoints.
 *
 * Paths confirmed by reading backend routers:
 *   - Asignaciones CRUD: /api/asignaciones (C-07 router)
 *   - Equipo operations: /api/equipos/* (C-08 router)
 *
 * No `any` allowed.
 */

import { api } from '@/shared/services/api'
import type {
  Asignacion,
  AsignacionFilters,
  AsignacionMasivaRequest,
  AsignacionMasivaResult,
  ClonarEquipoRequest,
  ClonarEquipoResponse,
  CreateAsignacionRequest,
  ModificarVigenciaRequest,
  ModificarVigenciaResponse,
  UsuarioBusquedaItem,
} from '../types'

const BASE_ASIGNACIONES = '/api/asignaciones'
const BASE_EQUIPOS = '/api/equipos'

// ---------------------------------------------------------------------------
// GET /api/asignaciones — list with optional filters
// ---------------------------------------------------------------------------

export async function getAsignaciones(
  filters?: AsignacionFilters,
): Promise<Asignacion[]> {
  const { data } = await api.get<Asignacion[]>(BASE_ASIGNACIONES, {
    params: filters,
  })
  return data
}

// ---------------------------------------------------------------------------
// POST /api/asignaciones — create individual asignacion
// ---------------------------------------------------------------------------

export async function createAsignacion(
  body: CreateAsignacionRequest,
): Promise<Asignacion> {
  const { data } = await api.post<Asignacion>(BASE_ASIGNACIONES, body)
  return data
}

// ---------------------------------------------------------------------------
// POST /api/equipos/asignaciones/masiva — bulk assign
// ---------------------------------------------------------------------------

export async function createMasiva(
  body: AsignacionMasivaRequest,
): Promise<AsignacionMasivaResult> {
  const { data } = await api.post<AsignacionMasivaResult>(
    `${BASE_EQUIPOS}/asignaciones/masiva`,
    body,
  )
  return data
}

// ---------------------------------------------------------------------------
// POST /api/equipos/asignaciones/clonar — clone team
// ---------------------------------------------------------------------------

export async function clonarEquipo(
  body: ClonarEquipoRequest,
): Promise<ClonarEquipoResponse> {
  const { data } = await api.post<ClonarEquipoResponse>(
    `${BASE_EQUIPOS}/asignaciones/clonar`,
    body,
  )
  return data
}

// ---------------------------------------------------------------------------
// PATCH /api/equipos/asignaciones/vigencia — bulk update dates
// ---------------------------------------------------------------------------

export async function updateVigencia(
  body: ModificarVigenciaRequest,
): Promise<ModificarVigenciaResponse> {
  const { data } = await api.patch<ModificarVigenciaResponse>(
    `${BASE_EQUIPOS}/asignaciones/vigencia`,
    body,
  )
  return data
}

// ---------------------------------------------------------------------------
// GET /api/equipos/asignaciones/exportar — CSV download as blob
// ---------------------------------------------------------------------------

export async function exportarEquipo(
  filters?: AsignacionFilters,
): Promise<Blob> {
  const { data } = await api.get<Blob>(`${BASE_EQUIPOS}/asignaciones/exportar`, {
    params: filters,
    responseType: 'blob',
  })
  return data
}

// ---------------------------------------------------------------------------
// GET /api/equipos/usuarios/buscar — autocomplete for docentes
// ---------------------------------------------------------------------------

export async function buscarUsuarios(q: string): Promise<UsuarioBusquedaItem[]> {
  const { data } = await api.get<UsuarioBusquedaItem[]>(
    `${BASE_EQUIPOS}/usuarios/buscar`,
    { params: { q } },
  )
  return data
}
