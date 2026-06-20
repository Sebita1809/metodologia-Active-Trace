/**
 * types.ts — TypeScript types for coordinacion/monitor-general feature.
 *
 * Source of truth: F2.7 — monitor global de alumnos del tenant.
 * Endpoint: GET /api/v1/calificaciones/monitor (path verified in design.md; not yet in router)
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// MonitorAlumno — single row in the monitor
// ---------------------------------------------------------------------------

export interface MonitorAlumno {
  alumno_id: string
  nombre: string
  apellidos: string
  email: string
  comision: string | null
  regional: string | null
  materia_id: string
  materia_nombre: string | null
  actividades_aprobadas: number
  total_actividades: number
  porcentaje_aprobacion: number
  estado_actividad: EstadoActividad
}

export type EstadoActividad = 'al_dia' | 'atrasado' | 'sin_datos'

// ---------------------------------------------------------------------------
// MonitorGeneralResponse
// ---------------------------------------------------------------------------

export interface MonitorGeneralResponse {
  items: MonitorAlumno[]
  total: number
}

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------

export interface MonitorGeneralFilters {
  materia_id?: string
  regional?: string
  comision?: string
  q?: string
  estado_actividad?: EstadoActividad
  criterio?: string
  page?: number
  page_size?: number
}
