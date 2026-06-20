/**
 * services/guardiasService.ts — API functions for guardias endpoints.
 *
 * Paths confirmed by reading backend/app/api/v1/routers/guardias.py:
 *   POST /api/v1/guardias — register guardia
 *   GET  /api/v1/guardias — list guardias (COORDINADOR/ADMIN)
 *
 * No `any` allowed.
 */

import { api } from '@/shared/services/api'
import type { Guardia, GuardiaFilters, RegistrarGuardiaRequest } from '../types'

const BASE = '/api/v1/guardias'

// ---------------------------------------------------------------------------
// GET /api/v1/guardias — list guardias with optional filters
// ---------------------------------------------------------------------------

export async function getGuardias(filters?: GuardiaFilters): Promise<Guardia[]> {
  const { data } = await api.get<Guardia[]>(BASE, { params: filters })
  return data
}

// ---------------------------------------------------------------------------
// POST /api/v1/guardias — register guardia
// ---------------------------------------------------------------------------

export async function createGuardia(
  body: RegistrarGuardiaRequest,
): Promise<Guardia> {
  const { data } = await api.post<Guardia>(BASE, body)
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/guardias — CSV export as blob
// ---------------------------------------------------------------------------

export async function exportarGuardias(
  filters?: GuardiaFilters,
): Promise<Blob> {
  const { data } = await api.get<Blob>(BASE, {
    params: { ...filters, format: 'csv' },
    responseType: 'blob',
  })
  return data
}
