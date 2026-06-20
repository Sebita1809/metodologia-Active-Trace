/**
 * services/facturasService.ts — API functions for facturas endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base path: /api/facturas
 *
 * Note: FacturaCreate uses JSON body (referencia_archivo is a string, not file upload).
 * Note: cambiar estado uses PATCH /api/facturas/{id}/estado
 */

import { api } from '@/shared/services/api'
import type { Factura, FacturaFilters, FacturaForm, CambiarEstadoForm } from '../types'

const BASE = '/api/facturas'

// ---------------------------------------------------------------------------
// GET /api/facturas — list facturas with optional filters
// ---------------------------------------------------------------------------

export async function getFacturas(filters: FacturaFilters = {}): Promise<Factura[]> {
  const { data } = await api.get<Factura[]>(BASE, {
    params: {
      ...(filters.usuario_id ? { usuario_id: filters.usuario_id } : {}),
      ...(filters.estado ? { estado: filters.estado } : {}),
      ...(filters.periodo_mes !== undefined ? { periodo_mes: filters.periodo_mes } : {}),
      ...(filters.periodo_anio !== undefined ? { periodo_anio: filters.periodo_anio } : {}),
      limit: filters.limit ?? 50,
      offset: filters.offset ?? 0,
    },
  })
  return data
}

// ---------------------------------------------------------------------------
// POST /api/facturas — create factura (JSON body, not multipart)
// ---------------------------------------------------------------------------

export async function createFactura(data: FacturaForm): Promise<Factura> {
  const { data: response } = await api.post<Factura>(BASE, data)
  return response
}

// ---------------------------------------------------------------------------
// PATCH /api/facturas/{id} — update factura fields
// ---------------------------------------------------------------------------

export async function updateFactura(
  id: string,
  data: Partial<FacturaForm>,
): Promise<Factura> {
  const { data: response } = await api.patch<Factura>(`${BASE}/${id}`, data)
  return response
}

// ---------------------------------------------------------------------------
// PATCH /api/facturas/{id}/estado — change estado (Pendiente → Abonada)
// ---------------------------------------------------------------------------

export async function cambiarEstadoFactura(
  id: string,
  data: CambiarEstadoForm,
): Promise<Factura> {
  const { data: response } = await api.patch<Factura>(`${BASE}/${id}/estado`, data)
  return response
}

// ---------------------------------------------------------------------------
// GET /api/facturas/{id} — single factura by id
// ---------------------------------------------------------------------------

export async function getFacturaById(id: string): Promise<Factura> {
  const { data } = await api.get<Factura>(`${BASE}/${id}`)
  return data
}
