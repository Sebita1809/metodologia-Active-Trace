/**
 * types/index.ts — TypeScript types for facturas feature.
 *
 * Mirror of backend Pydantic schemas (C-18):
 *   - factura.py: FacturaRead, FacturaCreate, FacturaUpdate, CambiarEstadoRequest
 *
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// Factura — single row
// ---------------------------------------------------------------------------

export type EstadoFactura = 'Pendiente' | 'Abonada'

export interface Factura {
  id: string
  tenant_id: string
  usuario_id: string
  periodo_mes: number
  periodo_anio: number
  detalle: string
  referencia_archivo: string | null
  tamano_kb: string | null
  monto: string
  estado: EstadoFactura
  abonada_at: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

// ---------------------------------------------------------------------------
// Filter params for GET /api/facturas
// ---------------------------------------------------------------------------

export interface FacturaFilters {
  usuario_id?: string
  estado?: EstadoFactura
  periodo_mes?: number
  periodo_anio?: number
  limit?: number
  offset?: number
}

// ---------------------------------------------------------------------------
// Create / update forms
// ---------------------------------------------------------------------------

export interface FacturaForm {
  usuario_id: string
  periodo_mes: number
  periodo_anio: number
  detalle: string
  referencia_archivo: string | null
  tamano_kb: string | null
  monto: string
}

export interface CambiarEstadoForm {
  nuevo_estado: EstadoFactura
}
