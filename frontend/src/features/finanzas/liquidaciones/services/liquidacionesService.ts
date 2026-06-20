/**
 * services/liquidacionesService.ts — API functions for liquidaciones endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base paths:
 *   Liquidaciones: /api/liquidaciones
 *   Grilla Base:   /api/liquidaciones/grilla/base
 *   Grilla Plus:   /api/liquidaciones/grilla/plus
 *
 * Key discrepancy from design.md:
 *   - cerrar uses POST /cerrar with body {cohorte_id, mes, anio} (NOT /{id}/cerrar)
 *   - Grilla paths are /grilla/base and /grilla/plus (NOT /salarios-base /plus)
 */

import { api } from '@/shared/services/api'
import type {
  CalcularLiquidacionRequest,
  CerrarLiquidacionRequest,
  LiquidacionRead,
  LiquidacionFilters,
  LiquidacionSegmentada,
} from '../types'

const BASE = '/api/liquidaciones'

// ---------------------------------------------------------------------------
// POST /api/liquidaciones/calcular — trigger calculation for a period
// ---------------------------------------------------------------------------

export async function calcularPeriodo(
  data: CalcularLiquidacionRequest,
): Promise<LiquidacionRead[]> {
  const { data: response } = await api.post<LiquidacionRead[]>(`${BASE}/calcular`, data)
  return response
}

// ---------------------------------------------------------------------------
// GET /api/liquidaciones/periodo — segmented view with KPIs
// ---------------------------------------------------------------------------

export async function getLiquidaciones(
  filters: LiquidacionFilters,
): Promise<LiquidacionSegmentada> {
  const { data } = await api.get<LiquidacionSegmentada>(`${BASE}/periodo`, {
    params: {
      cohorte_id: filters.cohorte_id,
      mes: filters.mes,
      anio: filters.anio,
    },
  })
  return data
}

// ---------------------------------------------------------------------------
// GET /api/liquidaciones/historial — all closed liquidaciones for this tenant
// ---------------------------------------------------------------------------

export async function getHistorial(): Promise<LiquidacionRead[]> {
  const { data } = await api.get<LiquidacionRead[]>(`${BASE}/historial`)
  return data
}

// ---------------------------------------------------------------------------
// POST /api/liquidaciones/cerrar — close all liquidaciones in a period (irreversible RN-22)
// ---------------------------------------------------------------------------

export async function cerrarLiquidacion(
  data: CerrarLiquidacionRequest,
): Promise<LiquidacionRead[]> {
  const { data: response } = await api.post<LiquidacionRead[]>(`${BASE}/cerrar`, data)
  return response
}

// ---------------------------------------------------------------------------
// GET /api/liquidaciones/{id} — single liquidacion by id
// ---------------------------------------------------------------------------

export async function getLiquidacionById(id: string): Promise<LiquidacionRead> {
  const { data } = await api.get<LiquidacionRead>(`${BASE}/${id}`)
  return data
}

// ---------------------------------------------------------------------------
// Export CSV — uses same /periodo endpoint, client-side blob download
// ---------------------------------------------------------------------------

export async function exportarLiquidacionCSV(filters: LiquidacionFilters): Promise<Blob> {
  const { data } = await api.get<LiquidacionSegmentada>(`${BASE}/periodo`, {
    params: {
      cohorte_id: filters.cohorte_id,
      mes: filters.mes,
      anio: filters.anio,
    },
  })

  // Build CSV from the segmented view
  const rows: string[] = [
    'Segmento,Usuario ID,Rol,Base,Plus,Total,Estado,Cerrada at',
  ]

  const addSegment = (segmento: string, liq: LiquidacionRead[]) => {
    for (const l of liq) {
      rows.push(
        [
          segmento,
          l.usuario_id,
          l.rol,
          l.base_monto,
          l.plus_monto,
          l.total_monto,
          l.estado,
          l.cerrada_at ?? '',
        ].join(','),
      )
    }
  }

  addSegment('General', data.general.liquidaciones)
  addSegment('NEXO', data.nexo.liquidaciones)
  addSegment('Facturantes', data.facturantes.liquidaciones)

  return new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' })
}
