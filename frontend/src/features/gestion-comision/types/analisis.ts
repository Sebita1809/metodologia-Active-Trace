/**
 * types/analisis.ts — TypeScript types mirroring backend Pydantic schemas
 * for analisis endpoints (C-11).
 *
 * Source of truth: backend/app/schemas/analisis.py
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// Atrasados — GET /api/v1/analisis/atrasados
// ---------------------------------------------------------------------------

export interface AlumnoAtrasado {
  alumno_id: string
  nombre: string
  apellidos: string
  actividades_faltantes: string[]
  actividades_reprobadas: string[]
}

export interface AtrasadosResponse {
  atrasados: AlumnoAtrasado[]
  sin_padron: boolean
}

// ---------------------------------------------------------------------------
// Ranking — GET /api/v1/analisis/ranking
// ---------------------------------------------------------------------------

export interface RankingItem {
  alumno_id: string
  nombre: string
  apellidos: string
  aprobadas: number
}

export interface RankingResponse {
  items: RankingItem[]
}

// ---------------------------------------------------------------------------
// Notas finales — GET /api/v1/analisis/notas-finales
// ---------------------------------------------------------------------------

export interface NotaFinalItem {
  alumno_id: string
  nombre: string
  apellidos: string
  aprobadas: number
  total_actividades: number
  porcentaje_aprobacion: number
}

export interface NotasFinalesResponse {
  items: NotaFinalItem[]
}

// ---------------------------------------------------------------------------
// Reporte — GET /api/v1/analisis/reporte
// ---------------------------------------------------------------------------

export interface ReporteAsignacion {
  total_alumnos: number
  total_atrasados: number
  pct_aprobacion_general: number
  total_actividades: number
  tiene_datos: boolean
}
