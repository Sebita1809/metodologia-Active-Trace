/**
 * types/index.ts — TypeScript types for auditoría feature.
 *
 * Mirror of backend Pydantic schemas (C-19):
 *   - auditoria.py: AccionesPorDiaResponse, ComunicacionesPorDocenteResponse,
 *                   InteraccionesDocenteMateriaResponse, UltimasAccionesResponse,
 *                   LogFiltradoResponse
 *
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// Acciones por día (serie temporal)
// ---------------------------------------------------------------------------

export interface AccionesPorDiaItem {
  dia: string  // ISO datetime truncated to day
  total: number
}

export interface AccionesPorDiaResponse {
  items: AccionesPorDiaItem[]
}

// ---------------------------------------------------------------------------
// Comunicaciones por docente
// ---------------------------------------------------------------------------

export interface ComunicacionesPorDocenteItem {
  actor_id: string
  pendiente: number
  enviando: number
  enviado: number
  fallido: number
  cancelado: number
}

export interface ComunicacionesPorDocenteResponse {
  items: ComunicacionesPorDocenteItem[]
}

// ---------------------------------------------------------------------------
// Interacciones docente × materia
// ---------------------------------------------------------------------------

export interface InteraccionesDocenteMateriaItem {
  actor_id: string
  materia_id: string | null
  total: number
}

export interface InteraccionesDocenteMateriaResponse {
  items: InteraccionesDocenteMateriaItem[]
}

// ---------------------------------------------------------------------------
// Audit log item (shared between panel and log completo)
// ---------------------------------------------------------------------------

export interface LogAuditoriaItem {
  id: string
  tenant_id: string
  fecha_hora: string
  actor_id: string
  impersonado_id: string | null
  materia_id: string | null
  accion: string
  detalle: Record<string, unknown> | null
  filas_afectadas: number
  ip: string | null
  user_agent: string | null
}

export interface UltimasAccionesResponse {
  items: LogAuditoriaItem[]
}

// ---------------------------------------------------------------------------
// Log filtrado (paginated)
// ---------------------------------------------------------------------------

export interface LogFiltradoResponse {
  items: LogAuditoriaItem[]
  total: number
  limit: number
  offset: number
}

// ---------------------------------------------------------------------------
// Filter params
// ---------------------------------------------------------------------------

export interface AuditoriaFilters {
  desde?: string
  hasta?: string
  materia_id?: string
  usuario_id?: string
  accion?: string
  estado?: string
  limit?: number
  offset?: number
}

export interface AccionesPorDiaFilters {
  desde: string
  hasta: string
}

// ---------------------------------------------------------------------------
// Composite type for AuditoriaPanelView
// ---------------------------------------------------------------------------

export interface AuditoriaPanelData {
  accionesPorDia: AccionesPorDiaResponse | null
  comunicacionesPorDocente: ComunicacionesPorDocenteResponse | null
  interaccionesDocente: InteraccionesDocenteMateriaResponse | null
  ultimasAcciones: UltimasAccionesResponse | null
}
