/**
 * services/usuariosAdminService.ts — API functions for admin/usuarios endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base path: /api/admin/usuarios
 *
 * SECURITY: CBU/alias NEVER sent in query strings (URL params).
 * All PII including CBU/alias_cbu goes only in request body JSON (POST/PATCH body).
 * Backend decrypts before returning in response — display as-is.
 */

import { api } from '@/shared/services/api'
import type { UsuarioAdmin, UsuarioAdminForm } from '../types'

const BASE = '/api/admin/usuarios'

// ---------------------------------------------------------------------------
// GET /api/admin/usuarios — list usuarios
// ---------------------------------------------------------------------------

export async function getUsuarios(): Promise<UsuarioAdmin[]> {
  const { data } = await api.get<UsuarioAdmin[]>(BASE)
  return data
}

// ---------------------------------------------------------------------------
// GET /api/admin/usuarios/{id} — single usuario
// ---------------------------------------------------------------------------

export async function getUsuarioById(id: string): Promise<UsuarioAdmin> {
  const { data } = await api.get<UsuarioAdmin>(`${BASE}/${id}`)
  return data
}

// ---------------------------------------------------------------------------
// POST /api/admin/usuarios — create usuario
// CBU/alias go only in body JSON (never in URL params) — SECURITY rule
// ---------------------------------------------------------------------------

export async function createUsuario(data: UsuarioAdminForm): Promise<UsuarioAdmin> {
  // Explicitly destructuring to confirm body-only sends (never params)
  const { data: response } = await api.post<UsuarioAdmin>(BASE, data)
  return response
}

// ---------------------------------------------------------------------------
// PATCH /api/admin/usuarios/{id} — update usuario
// CBU/alias go only in body JSON (never in URL params) — SECURITY rule
// ---------------------------------------------------------------------------

export async function updateUsuario(
  id: string,
  data: Partial<UsuarioAdminForm>,
): Promise<UsuarioAdmin> {
  // Body only — CBU/alias NEVER in URL params
  const { data: response } = await api.patch<UsuarioAdmin>(`${BASE}/${id}`, data)
  return response
}
