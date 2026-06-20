/**
 * services/grillaSalarialService.ts — API functions for grilla salarial endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base paths:
 *   Salario Base: /api/liquidaciones/grilla/base
 *   Salario Plus: /api/liquidaciones/grilla/plus
 *
 * Note: update uses PATCH (not PUT).
 * Note: delete returns 204 (no content).
 */

import { api } from '@/shared/services/api'
import type { SalarioBase, SalarioBaseForm, Plus, PlusForm } from '../types'

const BASE_BASE = '/api/liquidaciones/grilla/base'
const PLUS_BASE = '/api/liquidaciones/grilla/plus'

// ---------------------------------------------------------------------------
// Salario Base
// ---------------------------------------------------------------------------

export async function getSalariosBase(): Promise<SalarioBase[]> {
  const { data } = await api.get<SalarioBase[]>(BASE_BASE)
  return data
}

export async function createSalarioBase(data: SalarioBaseForm): Promise<SalarioBase> {
  const { data: response } = await api.post<SalarioBase>(BASE_BASE, data)
  return response
}

export async function updateSalarioBase(
  id: string,
  data: Partial<SalarioBaseForm>,
): Promise<SalarioBase> {
  const { data: response } = await api.patch<SalarioBase>(`${BASE_BASE}/${id}`, data)
  return response
}

export async function deleteSalarioBase(id: string): Promise<void> {
  await api.delete(`${BASE_BASE}/${id}`)
}

// ---------------------------------------------------------------------------
// Plus
// ---------------------------------------------------------------------------

export async function getPlus(): Promise<Plus[]> {
  const { data } = await api.get<Plus[]>(PLUS_BASE)
  return data
}

export async function createPlus(data: PlusForm): Promise<Plus> {
  const { data: response } = await api.post<Plus>(PLUS_BASE, data)
  return response
}

export async function updatePlus(id: string, data: Partial<PlusForm>): Promise<Plus> {
  const { data: response } = await api.patch<Plus>(`${PLUS_BASE}/${id}`, data)
  return response
}

export async function deletePlus(id: string): Promise<void> {
  await api.delete(`${PLUS_BASE}/${id}`)
}
