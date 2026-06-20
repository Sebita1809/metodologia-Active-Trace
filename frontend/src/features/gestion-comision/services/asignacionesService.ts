/**
 * services/asignacionesService.ts — API functions for listing asignaciones
 * (to populate the comision selector).
 *
 * The selector shows asignaciones where the authenticated user is PROFESOR or TUTOR.
 * The userId is NOT passed by the frontend — it comes from the JWT on the backend.
 * However, GET /api/asignaciones accepts optional usuario_id as a filter;
 * the frontend passes it from the decoded JWT claims (business data, not identity
 * substitution — the backend re-validates via JWT regardless).
 *
 * Base path: /api/asignaciones
 */

import { api } from '@/shared/services/api'
import type { AsignacionResponse } from '../types/asignaciones'

const BASE = '/api/asignaciones'

export async function listAsignaciones(params?: {
  usuario_id?: string
  rol?: string
}): Promise<AsignacionResponse[]> {
  const { data } = await api.get<AsignacionResponse[]>(BASE, { params })
  return data
}
