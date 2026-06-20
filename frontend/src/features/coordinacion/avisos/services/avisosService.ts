/**
 * services/avisosService.ts — API functions for avisos endpoints.
 *
 * Paths confirmed by reading backend routers:
 *   Base path: /api/avisos (C-15 router)
 *
 * No `any` allowed.
 */

import { api } from '@/shared/services/api'
import type { AckResponse, Aviso, CrearAvisoRequest, UpdateAvisoRequest } from '../types'

const BASE = '/api/avisos'

// ---------------------------------------------------------------------------
// GET /api/avisos — list all avisos (admin view with total_acks)
// ---------------------------------------------------------------------------

export async function getAvisos(): Promise<Aviso[]> {
  const { data } = await api.get<Aviso[]>(BASE)
  return data
}

// ---------------------------------------------------------------------------
// POST /api/avisos — create new aviso
// ---------------------------------------------------------------------------

export async function createAviso(body: CrearAvisoRequest): Promise<Aviso> {
  const { data } = await api.post<Aviso>(BASE, body)
  return data
}

// ---------------------------------------------------------------------------
// PATCH /api/avisos/{id} — update aviso
// ---------------------------------------------------------------------------

export async function updateAviso(
  id: string,
  body: UpdateAvisoRequest,
): Promise<Aviso> {
  const { data } = await api.patch<Aviso>(`${BASE}/${id}`, body)
  return data
}

// ---------------------------------------------------------------------------
// DELETE /api/avisos/{id} — soft delete aviso
// ---------------------------------------------------------------------------

export async function deleteAviso(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}

// ---------------------------------------------------------------------------
// GET /api/avisos/{id} total_acks — read from the aviso's total_acks field
// Using GET /api/avisos and filtering by id
// ---------------------------------------------------------------------------

export async function getAckCount(id: string): Promise<number> {
  const { data } = await api.get<Aviso>(`${BASE}/${id}`)
  return data.total_acks
}
