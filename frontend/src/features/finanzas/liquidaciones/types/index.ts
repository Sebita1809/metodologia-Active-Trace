/**
 * types/index.ts — TypeScript types for liquidaciones feature.
 *
 * Mirror of backend Pydantic schemas (C-18):
 *   - liquidacion.py: LiquidacionRead, PeriodoView, PeriodoSegmento,
 *                     CerrarRequest, CalcularRequest
 *   - salario_base.py, salario_plus.py (in grilla-salarial feature)
 *
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// Liquidacion — single row
// ---------------------------------------------------------------------------

export interface LiquidacionRead {
  id: string
  tenant_id: string
  usuario_id: string
  cohorte_id: string
  periodo_mes: number
  periodo_anio: number
  rol: string
  comisiones: unknown[]
  base_monto: string
  plus_monto: string
  total_monto: string
  desglose: Record<string, unknown> | null
  es_nexo: boolean
  excluido_por_factura: boolean
  estado: string
  cerrada_at: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

// ---------------------------------------------------------------------------
// PeriodoSegmento — one of the three segments in PeriodoView
// ---------------------------------------------------------------------------

export interface PeriodoSegmento {
  liquidaciones: LiquidacionRead[]
  total: string
}

// ---------------------------------------------------------------------------
// PeriodoView — segmented view with KPIs (F10.6)
// ---------------------------------------------------------------------------

export interface LiquidacionSegmentada {
  cohorte_id: string
  mes: number
  anio: number
  general: PeriodoSegmento
  nexo: PeriodoSegmento
  facturantes: PeriodoSegmento
  total_sin_factura: string
  total_con_factura: string
}

// ---------------------------------------------------------------------------
// Filter params for GET /api/liquidaciones/periodo
// ---------------------------------------------------------------------------

export interface LiquidacionFilters {
  cohorte_id: string
  mes: number
  anio: number
}

// ---------------------------------------------------------------------------
// Request bodies
// ---------------------------------------------------------------------------

export interface CalcularLiquidacionRequest {
  cohorte_id: string
  mes: number
  anio: number
}

export interface CerrarLiquidacionRequest {
  cohorte_id: string
  mes: number
  anio: number
}
