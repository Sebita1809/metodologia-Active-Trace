/**
 * types/index.ts — TypeScript types for admin/programas-fechas feature.
 *
 * Mirror of backend Pydantic schemas (C-17):
 *   - programas.py: ProgramaResponse, ProgramaCreate
 *   - fechas_academicas.py: FechaAcademicaResponse, FechaAcademicaCreate, FechaAcademicaUpdate
 *
 * IMPORTANT: programas use JSON body (NOT multipart). referencia_archivo is a string reference.
 *
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// ProgramaMateria
// ---------------------------------------------------------------------------

export type TipoFechaAcademica = 'parcial' | 'TP' | 'coloquio'

export interface ProgramaMateria {
  id: string
  tenant_id: string
  materia_id: string
  carrera_id: string
  cohorte_id: string
  titulo: string
  referencia_archivo: string  // string reference (URL or path) — NOT a file blob
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface ProgramaForm {
  materia_id: string
  carrera_id: string
  cohorte_id: string
  titulo: string
  referencia_archivo: string
}

export interface ProgramaFilters {
  materia_id?: string
  carrera_id?: string
  cohorte_id?: string
}

// ---------------------------------------------------------------------------
// FechaAcademica
// ---------------------------------------------------------------------------

export interface FechaAcademica {
  id: string
  tenant_id: string
  materia_id: string
  cohorte_id: string
  tipo: TipoFechaAcademica
  numero: number
  periodo: string | null
  fecha: string  // ISO date (YYYY-MM-DD)
  titulo: string
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface FechaAcademicaForm {
  materia_id: string
  cohorte_id: string
  tipo: TipoFechaAcademica
  numero: number
  fecha: string
  titulo: string
  periodo: string | null
}

export interface FechaAcademicaUpdateForm {
  fecha: string | null
  titulo: string | null
  periodo: string | null
}

export interface FechaAcademicaFilters {
  materia_id: string
  cohorte_id: string
}
