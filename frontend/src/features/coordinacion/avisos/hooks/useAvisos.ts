/**
 * hooks/useAvisos.ts — TanStack Query hooks for avisos endpoints.
 *
 * Hooks:
 *   useAvisos       — GET /api/avisos
 *   useCreateAviso  — POST /api/avisos
 *   useUpdateAviso  — PATCH /api/avisos/{id}
 *   useDeleteAviso  — DELETE /api/avisos/{id}
 *   useAckCount     — read total_acks from aviso detail
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAviso,
  deleteAviso,
  getAckCount,
  getAvisos,
  updateAviso,
} from '../services/avisosService'
import type { CrearAvisoRequest, UpdateAvisoRequest } from '../types'

export const avisosKeys = {
  all: ['coordinacion', 'avisos'] as const,
  list: () => [...avisosKeys.all, 'list'] as const,
  ackCount: (id: string) => [...avisosKeys.all, 'ack', id] as const,
}

// ---------------------------------------------------------------------------
// useAvisos
// ---------------------------------------------------------------------------

export function useAvisos() {
  return useQuery({
    queryKey: avisosKeys.list(),
    queryFn: () => getAvisos(),
  })
}

// ---------------------------------------------------------------------------
// useCreateAviso
// ---------------------------------------------------------------------------

export function useCreateAviso() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CrearAvisoRequest) => createAviso(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: avisosKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useUpdateAviso
// ---------------------------------------------------------------------------

export function useUpdateAviso() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UpdateAvisoRequest }) =>
      updateAviso(id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: avisosKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useDeleteAviso
// ---------------------------------------------------------------------------

export function useDeleteAviso() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteAviso(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: avisosKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useAckCount — read total_acks from single aviso
// ---------------------------------------------------------------------------

export function useAckCount(id: string) {
  return useQuery({
    queryKey: avisosKeys.ackCount(id),
    queryFn: () => getAckCount(id),
    enabled: !!id,
  })
}
