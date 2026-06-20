/**
 * types.ts — TypeScript types for coordinacion/tareas feature.
 *
 * Source of truth: backend/app/api/v1/routers/tareas.py
 * No `any` allowed.
 */

export type EstadoTarea = 'Abierta' | 'En progreso' | 'Completada' | 'Cerrada'

// ---------------------------------------------------------------------------
// Tarea — response from GET /api/v1/tareas
// ---------------------------------------------------------------------------

export interface Tarea {
  id: string
  tenant_id: string
  titulo: string
  descripcion: string
  criterio_cierre: string | null
  materia_id: string | null
  asignada_a: string
  asignada_por: string
  estado: EstadoTarea
  observacion: string | null
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Comentario de tarea — response from GET /api/v1/tareas/{id}/comentarios
// ---------------------------------------------------------------------------

export interface ComentarioTarea {
  id: string
  tarea_id: string
  autor_id: string
  texto: string
  created_at: string
}

// ---------------------------------------------------------------------------
// Create tarea — POST /api/v1/tareas
// ---------------------------------------------------------------------------

export interface CrearTareaRequest {
  titulo: string
  descripcion: string
  criterio_cierre?: string | null
  materia_id?: string | null
  asignada_a: string
}

// ---------------------------------------------------------------------------
// Cambiar estado — PATCH /api/v1/tareas/{id}/estado
// ---------------------------------------------------------------------------

export interface CambiarEstadoTareaRequest {
  estado: EstadoTarea
  observacion?: string | null
}

// ---------------------------------------------------------------------------
// Filters for GET /api/v1/tareas
// ---------------------------------------------------------------------------

export interface TareaFilters {
  asignada_a?: string
  asignada_por?: string
  materia_id?: string
  estado?: EstadoTarea
  q?: string
}
