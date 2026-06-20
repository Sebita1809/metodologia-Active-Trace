/**
 * types.ts — TypeScript types for coordinacion/equipos feature.
 *
 * Source of truth: backend/app/api/v1/routers/equipos.py and asignaciones.py
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// Asignacion
// ---------------------------------------------------------------------------

export type EstadoVigencia = 'Vigente' | 'Vencida'

export interface Asignacion {
  id: string
  tenant_id: string
  usuario_id: string
  rol: string
  materia_id: string | null
  carrera_id: string | null
  cohorte_id: string | null
  comisiones: string[]
  responsable_id: string | null
  desde: string
  hasta: string | null
  estado_vigencia: EstadoVigencia
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Filters for GET /api/asignaciones
// ---------------------------------------------------------------------------

export interface AsignacionFilters {
  usuario_id?: string
  materia_id?: string
  carrera_id?: string
  cohorte_id?: string
  rol?: string
  responsable_id?: string
}

// ---------------------------------------------------------------------------
// Create asignacion — POST /api/asignaciones
// ---------------------------------------------------------------------------

export interface CreateAsignacionRequest {
  usuario_id: string
  rol: string
  desde: string
  hasta?: string | null
  materia_id?: string | null
  carrera_id?: string | null
  cohorte_id?: string | null
  comisiones?: string[]
  responsable_id?: string | null
}

// ---------------------------------------------------------------------------
// Asignacion masiva — POST /api/equipos/asignaciones/masiva
// ---------------------------------------------------------------------------

export interface AsignacionMasivaRequest {
  usuario_ids: string[]
  rol: string
  desde: string
  hasta?: string | null
  materia_id?: string | null
  carrera_id?: string | null
  cohorte_id?: string | null
}

export interface AsignacionMasivaItemResult {
  usuario_id: string
  success: boolean
  asignacion_id?: string | null
  error?: string | null
}

export interface AsignacionMasivaResult {
  resultados: AsignacionMasivaItemResult[]
  total: number
  exitosos: number
  fallidos: number
}

// ---------------------------------------------------------------------------
// Clonar equipo — POST /api/equipos/asignaciones/clonar
// ---------------------------------------------------------------------------

export interface ClonarEquipoRequest {
  origen_materia_id: string
  origen_carrera_id: string
  origen_cohorte_id: string
  destino_materia_id: string
  destino_carrera_id: string
  destino_cohorte_id: string
  desde?: string | null
  hasta?: string | null
}

export interface ClonarEquipoResponse {
  asignaciones_creadas: number
  advertencia?: string | null
}

// ---------------------------------------------------------------------------
// Modificar vigencia — PATCH /api/equipos/asignaciones/vigencia
// ---------------------------------------------------------------------------

export interface ModificarVigenciaRequest {
  materia_id: string
  carrera_id: string
  cohorte_id: string
  desde: string
  hasta?: string | null
}

export interface ModificarVigenciaResponse {
  actualizadas: number
}

// ---------------------------------------------------------------------------
// Usuario buscar — GET /api/equipos/usuarios/buscar
// ---------------------------------------------------------------------------

export interface UsuarioBusquedaItem {
  id: string
  nombre: string
  apellidos: string
  email: string
}
