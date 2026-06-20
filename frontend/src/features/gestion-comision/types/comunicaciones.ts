/**
 * types/comunicaciones.ts — TypeScript types mirroring backend Pydantic schemas
 * for comunicaciones endpoints (C-12).
 *
 * Source of truth: backend/app/schemas/comunicacion.py + models/comunicacion.py
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// Estado (state machine: Pendiente → Enviando → Enviado | Error | Cancelado)
// ---------------------------------------------------------------------------

export type EstadoComunicacion =
  | 'Pendiente'
  | 'Enviando'
  | 'Enviado'
  | 'Error'
  | 'Cancelado'

/** Terminal states — polling stops when all messages are in a terminal state */
export const ESTADOS_TERMINALES: EstadoComunicacion[] = ['Enviado', 'Error', 'Cancelado']

export function isEstadoTerminal(estado: EstadoComunicacion): boolean {
  return ESTADOS_TERMINALES.includes(estado)
}

// ---------------------------------------------------------------------------
// ComunicacionRead — response schema for queue items
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
// Preview — POST /api/comunicaciones/preview
// ---------------------------------------------------------------------------

export interface DestinatarioPreview {
  email: string
  variables: Record<string, string>
}

export interface PreviewRequest {
  materia_id: string
  asunto: string
  cuerpo: string
  destinatarios: DestinatarioPreview[]
}

export interface RenderResult {
  email: string
  asunto_renderizado: string
  cuerpo_renderizado: string
}

export interface PreviewResponse {
  resultados: RenderResult[]
}

// ---------------------------------------------------------------------------
// Encolar lote — POST /api/comunicaciones/
// ---------------------------------------------------------------------------

export interface DestinatarioLote {
  email: string
  variables: Record<string, string>
}

export interface EncolarLoteRequest {
  materia_id: string
  asunto: string
  cuerpo: string
  destinatarios: DestinatarioLote[]
}

export interface EncolarLoteResponse {
  lote_id: string
  cantidad: number
}
