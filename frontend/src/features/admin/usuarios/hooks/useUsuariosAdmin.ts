/**
 * hooks/useUsuariosAdmin.ts — TanStack Query hooks for admin/usuarios endpoints.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createUsuario,
  getUsuarios,
  updateUsuario,
} from '../services/usuariosAdminService'
import type { UsuarioAdminForm } from '../types'

// Query key factories
export const usuariosAdminKeys = {
  all: ['usuarios-admin'] as const,
  list: () => [...usuariosAdminKeys.all, 'list'] as const,
}

// ---------------------------------------------------------------------------
// useUsuariosAdmin — query for GET /api/admin/usuarios
// ---------------------------------------------------------------------------

export function useUsuariosAdmin() {
  return useQuery({
    queryKey: usuariosAdminKeys.list(),
    queryFn: getUsuarios,
  })
}

// ---------------------------------------------------------------------------
// useCreateUsuarioAdmin — mutation for POST /api/admin/usuarios
// CBU/alias go in body only (service enforces this)
// ---------------------------------------------------------------------------

export function useCreateUsuarioAdmin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: UsuarioAdminForm) => createUsuario(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: usuariosAdminKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useUpdateUsuarioAdmin — mutation for PATCH /api/admin/usuarios/{id}
// CBU/alias go in body only (service enforces this)
// ---------------------------------------------------------------------------

export function useUpdateUsuarioAdmin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string
      data: Partial<UsuarioAdminForm>
    }) => updateUsuario(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: usuariosAdminKeys.all })
    },
  })
}
