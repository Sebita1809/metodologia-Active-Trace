/**
 * hooks/useTareas.ts — TanStack Query hooks for tareas endpoints.
 *
 * Hooks:
 *   useMisTareas      — GET /api/v1/tareas/mias
 *   useTareas         — GET /api/v1/tareas (admin, with filters)
 *   useCreateTarea    — POST /api/v1/tareas
 *   useUpdateTarea    — PATCH /api/v1/tareas/{id}/estado
 *   useAddComentario  — POST /api/v1/tareas/{id}/comentarios
 *   useComentarios    — GET /api/v1/tareas/{id}/comentarios
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  addComentario,
  createTarea,
  getComentarios,
  getMisTareas,
  getTareas,
  updateEstadoTarea,
} from '../services/tareasService'
import type {
  CambiarEstadoTareaRequest,
  CrearTareaRequest,
  TareaFilters,
} from '../types'

export const tareasKeys = {
  all: ['coordinacion', 'tareas'] as const,
  mias: () => [...tareasKeys.all, 'mias'] as const,
  list: (filters?: TareaFilters) =>
    [...tareasKeys.all, 'list', filters ?? {}] as const,
  comentarios: (id: string) => [...tareasKeys.all, 'comentarios', id] as const,
}

// ---------------------------------------------------------------------------
// useMisTareas
// ---------------------------------------------------------------------------

export function useMisTareas() {
  return useQuery({
    queryKey: tareasKeys.mias(),
    queryFn: () => getMisTareas(),
  })
}

// ---------------------------------------------------------------------------
// useTareas — admin view with filters
// ---------------------------------------------------------------------------

export function useTareas(filters?: TareaFilters) {
  return useQuery({
    queryKey: tareasKeys.list(filters),
    queryFn: () => getTareas(filters),
  })
}

// ---------------------------------------------------------------------------
// useCreateTarea
// ---------------------------------------------------------------------------

export function useCreateTarea() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CrearTareaRequest) => createTarea(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: tareasKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useUpdateTarea — change estado
// ---------------------------------------------------------------------------

export function useUpdateTarea() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CambiarEstadoTareaRequest }) =>
      updateEstadoTarea(id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: tareasKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useAddComentario
// ---------------------------------------------------------------------------

export function useAddComentario() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, texto }: { id: string; texto: string }) =>
      addComentario(id, texto),
    onSuccess: (_data, { id }) => {
      void queryClient.invalidateQueries({ queryKey: tareasKeys.comentarios(id) })
    },
  })
}

// ---------------------------------------------------------------------------
// useComentarios
// ---------------------------------------------------------------------------

export function useComentarios(tareaId: string | null) {
  return useQuery({
    queryKey: tareasKeys.comentarios(tareaId ?? ''),
    queryFn: () => getComentarios(tareaId!),
    enabled: tareaId !== null,
  })
}
