/**
 * services/fechasAcademicasService.ts — API functions for fechas académicas endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base path: /api/v1/fechas-academicas
 *
 * Note: GET / requires BOTH materia_id AND cohorte_id as required query params.
 * Note: update uses PATCH (only fecha, titulo, periodo fields).
 */

import { api } from '@/shared/services/api'
import type {
  FechaAcademica,
  FechaAcademicaForm,
  FechaAcademicaUpdateForm,
  FechaAcademicaFilters,
} from '../types'

const BASE = '/api/v1/fechas-academicas'

// ---------------------------------------------------------------------------
// GET /api/v1/fechas-academicas — list by materia × cohorte (both required)
// ---------------------------------------------------------------------------

export async function getFechasAcademicas(
  filters: FechaAcademicaFilters,
): Promise<FechaAcademica[]> {
  const { data } = await api.get<FechaAcademica[]>(BASE, {
    params: {
      materia_id: filters.materia_id,
      cohorte_id: filters.cohorte_id,
    },
  })
  return data
}

// ---------------------------------------------------------------------------
// POST /api/v1/fechas-academicas — create a new fecha
// ---------------------------------------------------------------------------

export async function createFecha(data: FechaAcademicaForm): Promise<FechaAcademica> {
  const { data: response } = await api.post<FechaAcademica>(BASE, data)
  return response
}

// ---------------------------------------------------------------------------
// PATCH /api/v1/fechas-academicas/{id} — partial update (fecha, titulo, periodo)
// ---------------------------------------------------------------------------

export async function updateFecha(
  id: string,
  data: FechaAcademicaUpdateForm,
): Promise<FechaAcademica> {
  const { data: response } = await api.patch<FechaAcademica>(`${BASE}/${id}`, data)
  return response
}

// ---------------------------------------------------------------------------
// DELETE /api/v1/fechas-academicas/{id} — soft-delete
// ---------------------------------------------------------------------------

export async function deleteFecha(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
