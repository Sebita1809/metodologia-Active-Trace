/**
 * types/asignaciones.ts — TypeScript types for asignacion selector.
 *
 * Source of truth: backend/app/schemas/asignacion.py
 * No `any` allowed.
 */

export type EstadoVigencia = 'Vigente' | 'Vencida'

export interface AsignacionResponse {
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
