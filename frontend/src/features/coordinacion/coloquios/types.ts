/**
 * types.ts — TypeScript types for coordinacion/coloquios feature.
 *
 * Source of truth: backend/app/api/v1/routers/coloquios.py
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// Evaluacion (convocatoria) — response from GET /api/v1/coloquios
// ---------------------------------------------------------------------------

export interface DiaDisponible {
  fecha: string
  cupos: number
}

export interface Evaluacion {
  id: string
  tenant_id: string
  materia_id: string
  instancia: number
  dias_disponibles: DiaDisponible[]
  activa: boolean
  total_convocados: number
  reservas_activas: number
  cupos_libres: number
  notas_registradas: number
  created_at: string
}

export interface EvaluacionConMetricas extends Evaluacion {
  cupos_totales: number
}

// ---------------------------------------------------------------------------
// Metricas panel — GET /api/v1/coloquios/metricas
// ---------------------------------------------------------------------------

export interface MetricasColoquios {
  total_alumnos_cargados: number
  instancias_activas: number
  reservas_activas: number
  notas_registradas: number
}

// ---------------------------------------------------------------------------
// Create evaluacion — POST /api/v1/coloquios
// ---------------------------------------------------------------------------

export interface CrearEvaluacionRequest {
  materia_id: string
  instancia: number
  dias_disponibles: DiaDisponible[]
}

// ---------------------------------------------------------------------------
// Importar alumnos — POST /api/v1/coloquios/{id}/alumnos
// ---------------------------------------------------------------------------

export interface ImportarPadronResponse {
  importados: number
  errores: string[]
}

// ---------------------------------------------------------------------------
// Reserva — response from GET /api/v1/coloquios/{id}/reservas
// ---------------------------------------------------------------------------

export interface Reserva {
  id: string
  evaluacion_id: string
  alumno_id: string
  fecha_reservada: string
  turno: number
  created_at: string
}

// ---------------------------------------------------------------------------
// Resultado coloquio — response from GET /api/v1/coloquios/{id}/resultados
// ---------------------------------------------------------------------------

export interface ResultadoColoquio {
  id: string
  evaluacion_id: string
  alumno_id: string
  instancia: number
  nota: number | null
  aprobado: boolean
  created_at: string
}
