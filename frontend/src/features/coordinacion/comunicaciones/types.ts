/**
 * types.ts — TypeScript types for coordinacion/comunicaciones feature.
 *
 * Covers the approval queue for pending communication batches.
 * Source of truth: backend/app/api/v1/routers/comunicaciones.py
 * No `any` allowed.
 */

export type EstadoComunicacion =
  | 'Pendiente'
  | 'Enviando'
  | 'Enviado'
  | 'Error'
  | 'Cancelado'

// ---------------------------------------------------------------------------
// ComunicacionRead — a single queue item
// ---------------------------------------------------------------------------

export interface ComunicacionRead {
  id: string
  tenant_id: string
  enviado_por: string
  materia_id: string
  destinatario: string
  asunto: string
  cuerpo: string
  estado: EstadoComunicacion
  lote_id: string
  enviado_at: string | null
  aprobado_at: string | null
  aprobado_por: string | null
  created_at: string
}

// ---------------------------------------------------------------------------
// LoteComunicacion — grouped by lote_id for the approval queue view
// ---------------------------------------------------------------------------

export interface LoteComunicacion {
  lote_id: string
  enviado_por: string
  materia_id: string
  estado: EstadoComunicacion
  cantidad: number
  created_at: string
  items: ComunicacionRead[]
}

// ---------------------------------------------------------------------------
// Approve/Cancel request bodies — POST /api/comunicaciones/aprobar|cancelar
// ---------------------------------------------------------------------------

export interface AprobarLoteRequest {
  lote_id: string
}

export interface CancelarLoteRequest {
  lote_id: string
}

export interface AprobacionResponse {
  actualizados: number
}

export interface CancelacionResponse {
  cancelados: number
}
