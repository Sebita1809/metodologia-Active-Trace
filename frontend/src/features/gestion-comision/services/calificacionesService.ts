/**
 * services/calificacionesService.ts — API functions for calificaciones endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base path: /api/calificaciones
 */

import { api } from '@/shared/services/api'
import type {
  CalificacionRead,
  FinalizacionPreviewResponse,
  ImportConfirmRequest,
  ImportPreviewResponse,
  UmbralMateriaRead,
  UmbralMateriaUpsert,
} from '../types/calificaciones'

const BASE = '/api/calificaciones'

// ---------------------------------------------------------------------------
// POST /api/calificaciones/preview
// multipart: file + asignacion_id form field
// ---------------------------------------------------------------------------

export async function previewImport(
  file: File,
  asignacion_id: string,
): Promise<ImportPreviewResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('asignacion_id', asignacion_id)

  const { data } = await api.post<ImportPreviewResponse>(`${BASE}/preview`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ---------------------------------------------------------------------------
// POST /api/calificaciones/import
// multipart: file + "request" JSON-encoded form field
// ---------------------------------------------------------------------------

export async function confirmImport(
  file: File,
  request: ImportConfirmRequest,
): Promise<CalificacionRead[]> {
  const form = new FormData()
  form.append('file', file)
  form.append('request', JSON.stringify(request))

  const { data } = await api.post<CalificacionRead[]>(`${BASE}/import`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ---------------------------------------------------------------------------
// POST /api/calificaciones/finalizacion-preview
// multipart: file + asignacion_id form field
// ---------------------------------------------------------------------------

export async function previewFinalizacion(
  file: File,
  asignacion_id: string,
): Promise<FinalizacionPreviewResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('asignacion_id', asignacion_id)

  const { data } = await api.post<FinalizacionPreviewResponse>(
    `${BASE}/finalizacion-preview`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

// ---------------------------------------------------------------------------
// GET /api/calificaciones?asignacion_id=...
// ---------------------------------------------------------------------------

export async function listCalificaciones(
  asignacion_id: string,
): Promise<CalificacionRead[]> {
  const { data } = await api.get<CalificacionRead[]>(BASE, {
    params: { asignacion_id },
  })
  return data
}

// ---------------------------------------------------------------------------
// GET /api/calificaciones/umbral?asignacion_id=...
// ---------------------------------------------------------------------------

export async function getUmbral(asignacion_id: string): Promise<UmbralMateriaRead> {
  const { data } = await api.get<UmbralMateriaRead>(`${BASE}/umbral`, {
    params: { asignacion_id },
  })
  return data
}

// ---------------------------------------------------------------------------
// PUT /api/calificaciones/umbral?asignacion_id=...&materia_id=...
// ---------------------------------------------------------------------------

export async function upsertUmbral(
  asignacion_id: string,
  materia_id: string,
  body: UmbralMateriaUpsert,
): Promise<UmbralMateriaRead> {
  const { data } = await api.put<UmbralMateriaRead>(`${BASE}/umbral`, body, {
    params: { asignacion_id, materia_id },
  })
  return data
}
