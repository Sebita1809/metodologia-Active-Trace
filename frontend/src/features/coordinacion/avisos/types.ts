/**
 * types.ts — TypeScript types for coordinacion/avisos feature.
 *
 * Source of truth: backend/app/api/v1/routers/avisos.py
 * No `any` allowed.
 */

export type SeveridadAviso = 'info' | 'advertencia' | 'critica'
export type AlcanceAviso = 'global' | 'materia' | 'cohorte'

// ---------------------------------------------------------------------------
// Aviso — response from GET/POST /api/avisos
// ---------------------------------------------------------------------------

export interface Aviso {
  id: string
  tenant_id: string
  titulo: string
  cuerpo: string
  alcance: AlcanceAviso
  materia_id: string | null
  cohorte_id: string | null
  roles_destinatarios: string[]
  severidad: SeveridadAviso
  fecha_inicio: string
  fecha_fin: string | null
  orden: number
  activo: boolean
  require_ack: boolean
  total_acks: number
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Create aviso — POST /api/avisos
// ---------------------------------------------------------------------------

export interface CrearAvisoRequest {
  titulo: string
  cuerpo: string
  alcance: AlcanceAviso
  materia_id?: string | null
  cohorte_id?: string | null
  roles_destinatarios: string[]
  severidad: SeveridadAviso
  fecha_inicio: string
  fecha_fin?: string | null
  orden?: number
  activo?: boolean
  require_ack?: boolean
}

// ---------------------------------------------------------------------------
// Update aviso — PATCH /api/avisos/{id}
// ---------------------------------------------------------------------------

export interface UpdateAvisoRequest {
  titulo?: string
  cuerpo?: string
  alcance?: AlcanceAviso
  materia_id?: string | null
  cohorte_id?: string | null
  roles_destinatarios?: string[]
  severidad?: SeveridadAviso
  fecha_inicio?: string
  fecha_fin?: string | null
  orden?: number
  activo?: boolean
  require_ack?: boolean
}

// ---------------------------------------------------------------------------
// Ack — POST /api/avisos/{id}/ack
// ---------------------------------------------------------------------------

export interface AckResponse {
  aviso_id: string
  usuario_id: string
  acknowledged_at: string
}
