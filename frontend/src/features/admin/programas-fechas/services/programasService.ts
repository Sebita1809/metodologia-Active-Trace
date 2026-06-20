/**
 * services/programasService.ts — API functions for programas de materia endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base path: /api/v1/programas
 *
 * IMPORTANT: ProgramaCreate uses JSON body (NOT multipart/form-data).
 * 'referencia_archivo' is a string reference (URL or path) — the binary file upload
 * is handled separately (if applicable). The backend receives JSON.
 */

import { api } from '@/shared/services/api'
import type { ProgramaMateria, ProgramaForm, ProgramaFilters } from '../types'

const BASE = '/api/v1/programas'

// ---------------------------------------------------------------------------
// GET /api/v1/programas — list programmes with optional filters
// ---------------------------------------------------------------------------

export async function getProgramas(
  filters: ProgramaFilters = {},
): Promise<ProgramaMateria[]> {
  const { data } = await api.get<ProgramaMateria[]>(BASE, {
    params: {
      ...(filters.materia_id ? { materia_id: filters.materia_id } : {}),
      ...(filters.carrera_id ? { carrera_id: filters.carrera_id } : {}),
      ...(filters.cohorte_id ? { cohorte_id: filters.cohorte_id } : {}),
    },
  })
  return data
}

// ---------------------------------------------------------------------------
// POST /api/v1/programas — create or replace programme (JSON body)
// If a vivo programme exists for the combo, backend soft-deletes it first.
// ---------------------------------------------------------------------------

export async function createPrograma(data: ProgramaForm): Promise<ProgramaMateria> {
  const { data: response } = await api.post<ProgramaMateria>(BASE, data)
  return response
}
