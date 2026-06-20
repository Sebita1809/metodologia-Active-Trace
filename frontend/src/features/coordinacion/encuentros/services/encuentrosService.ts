/**
 * services/encuentrosService.ts — API functions for encuentros endpoints.
 *
 * Paths confirmed by reading backend/app/api/v1/routers/encuentros.py:
 *   Admin view: GET /api/v1/admin/encuentros (C-13 router, task 9.4)
 *
 * No `any` allowed.
 */

import { api } from '@/shared/services/api'
import type { Encuentro, EncuentroFilters } from '../types'

const BASE_ADMIN = '/api/v1/admin/encuentros'

// ---------------------------------------------------------------------------
// GET /api/v1/admin/encuentros — transversal view for COORDINADOR/ADMIN
// ---------------------------------------------------------------------------

export async function getEncuentrosTenant(
  filters?: EncuentroFilters,
): Promise<Encuentro[]> {
  const { data } = await api.get<Encuentro[]>(BASE_ADMIN, { params: filters })
  return data
}
