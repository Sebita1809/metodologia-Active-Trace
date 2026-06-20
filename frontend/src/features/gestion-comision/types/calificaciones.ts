/**
 * types/calificaciones.ts — TypeScript types mirroring backend Pydantic schemas
 * for calificaciones endpoints (C-10).
 *
 * Source of truth: backend/app/schemas/calificacion.py + umbral_materia.py
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// CalificacionRead — GET /api/calificaciones response item
// ---------------------------------------------------------------------------

export type OrigenEnum = 'Importado' | 'Manual'

export interface CalificacionRead {
  id: string
  entrada_padron_id: string
  materia_id: string
  actividad: string
  nota_numerica: string | null
  nota_textual: string | null
  aprobado: boolean
  origen: OrigenEnum
  importado_at: string | null
  created_at: string
}

// ---------------------------------------------------------------------------
// Import preview — POST /api/calificaciones/preview
// ---------------------------------------------------------------------------

export interface ImportPreviewRequest {
  /** multipart: file + asignacion_id form field */
  asignacion_id: string
}

export interface ImportPreviewResponse {
  actividades_numericas: string[]
  actividades_textuales: string[]
  alumnos_detectados: number
}

// ---------------------------------------------------------------------------
// Import confirm — POST /api/calificaciones/import
// ---------------------------------------------------------------------------

/** Sent as JSON-encoded form field "request" alongside the file */
export interface ImportConfirmRequest {
  asignacion_id: string
  actividades_seleccionadas: string[]
}

// response is CalificacionRead[]

// ---------------------------------------------------------------------------
// Finalizacion preview — POST /api/calificaciones/finalizacion-preview
// ---------------------------------------------------------------------------

export interface FinalizacionItem {
  alumno_email: string
  actividad: string
}

export interface FinalizacionPreviewResponse {
  items: FinalizacionItem[]
}

// ---------------------------------------------------------------------------
// Umbral — GET/PUT /api/calificaciones/umbral
// ---------------------------------------------------------------------------

export interface UmbralMateriaRead {
  id: string
  asignacion_id: string
  materia_id: string
  umbral_pct: number
  valores_aprobatorios: string[]
}

export interface UmbralMateriaUpsert {
  umbral_pct: number
  valores_aprobatorios: string[]
}

// Default values as per backend RN-01/RN-02
export const UMBRAL_DEFAULT_PCT = 60
export const UMBRAL_DEFAULT_VALORES = ['Satisfactorio', 'Supera lo esperado']
