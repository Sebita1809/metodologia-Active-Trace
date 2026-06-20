/**
 * types.ts — TypeScript types for coordinacion/encuentros feature.
 *
 * Source of truth: backend/app/api/v1/routers/encuentros.py and guardias.py
 * No `any` allowed.
 */

export type EstadoEncuentro = 'Programado' | 'Realizado' | 'Cancelado'
export type EstadoGuardia = 'Registrada' | 'Auditada' | 'Rechazada'

// ---------------------------------------------------------------------------
// Encuentro — response from GET /api/v1/admin/encuentros
// ---------------------------------------------------------------------------

export interface Encuentro {
  id: string
  tenant_id: string
  asignacion_id: string
  materia_id: string | null
  docente_id: string
  fecha: string
  horario_inicio: string | null
  horario_fin: string | null
  estado: EstadoEncuentro
  enlace_grabacion: string | null
  created_at: string
}

// ---------------------------------------------------------------------------
// Filters for GET /api/v1/admin/encuentros
// ---------------------------------------------------------------------------

export interface EncuentroFilters {
  docente_id?: string
  materia_id?: string
  mes?: string  // YYYY-MM
}

// ---------------------------------------------------------------------------
// Guardia — response from GET /api/v1/guardias
// ---------------------------------------------------------------------------

export interface Guardia {
  id: string
  tenant_id: string
  asignacion_id: string
  cubierto_por: string
  materia_id: string | null
  carrera_id: string | null
  cohorte_id: string | null
  dia: string
  horario: string
  estado: EstadoGuardia
  comentarios: string | null
  created_at: string
}

// ---------------------------------------------------------------------------
// Registrar guardia — POST /api/v1/guardias
// ---------------------------------------------------------------------------

export interface RegistrarGuardiaRequest {
  asignacion_id: string
  cubierto_por: string
  materia_id?: string | null
  carrera_id?: string | null
  cohorte_id?: string | null
  dia: string
  horario: string
  estado?: EstadoGuardia
  comentarios?: string | null
}

// ---------------------------------------------------------------------------
// Filters for GET /api/v1/guardias
// ---------------------------------------------------------------------------

export interface GuardiaFilters {
  asignacion_id?: string
  fecha_desde?: string
  fecha_hasta?: string
}
