/**
 * types/index.ts — TypeScript types for admin/estructura feature.
 *
 * Mirror of backend Pydantic schemas (C-06):
 *   - carrera.py: CarreraResponse, CarreraCreate, CarreraUpdate
 *   - cohorte.py: CohorteResponse, CohorteCreate, CohorteUpdate
 *   - materia.py: (assumed similar pattern)
 *
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// Carrera
// ---------------------------------------------------------------------------

export type EstadoCarrera = 'Activa' | 'Inactiva'

export interface Carrera {
  id: string
  tenant_id: string
  codigo: string
  nombre: string
  estado: EstadoCarrera
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface CarreraForm {
  codigo: string
  nombre: string
  estado: EstadoCarrera
}

// ---------------------------------------------------------------------------
// Cohorte
// ---------------------------------------------------------------------------

export type EstadoCohorte = 'Activa' | 'Inactiva'

export interface Cohorte {
  id: string
  tenant_id: string
  carrera_id: string
  nombre: string
  anio: number
  vig_desde: string  // ISO date (YYYY-MM-DD)
  vig_hasta: string | null
  estado: EstadoCohorte
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface CohorteForm {
  carrera_id: string
  nombre: string
  anio: number
  vig_desde: string
  vig_hasta: string | null
  estado: EstadoCohorte
}

// ---------------------------------------------------------------------------
// Materia
// ---------------------------------------------------------------------------

export type EstadoMateria = 'Activa' | 'Inactiva'

export interface Materia {
  id: string
  tenant_id: string
  nombre: string
  codigo: string | null
  estado: EstadoMateria
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface MateriaForm {
  nombre: string
  codigo: string | null
  estado: EstadoMateria
}
