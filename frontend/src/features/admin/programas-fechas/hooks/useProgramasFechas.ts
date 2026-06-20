/**
 * hooks/useProgramasFechas.ts — TanStack Query hooks for programas y fechas académicas.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createPrograma, getProgramas } from '../services/programasService'
import {
  createFecha,
  deleteFecha,
  getFechasAcademicas,
  updateFecha,
} from '../services/fechasAcademicasService'
import type {
  ProgramaFilters,
  ProgramaForm,
  FechaAcademicaFilters,
  FechaAcademicaForm,
  FechaAcademicaUpdateForm,
} from '../types'

// Query key factories
export const programasKeys = {
  all: ['programas'] as const,
  list: (filters: ProgramaFilters) => [...programasKeys.all, 'list', filters] as const,
}

export const fechasKeys = {
  all: ['fechas-academicas'] as const,
  list: (filters: FechaAcademicaFilters) =>
    [...fechasKeys.all, 'list', filters] as const,
}

// ---------------------------------------------------------------------------
// Programas hooks
// ---------------------------------------------------------------------------

export function useProgramas(filters: ProgramaFilters = {}) {
  return useQuery({
    queryKey: programasKeys.list(filters),
    queryFn: () => getProgramas(filters),
  })
}

export function useCreatePrograma() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ProgramaForm) => createPrograma(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: programasKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// Fechas académicas hooks
// ---------------------------------------------------------------------------

export function useFechasAcademicas(filters: FechaAcademicaFilters | null) {
  return useQuery({
    queryKey: fechasKeys.list(
      filters ?? { materia_id: '', cohorte_id: '' },
    ),
    queryFn: () => getFechasAcademicas(filters!),
    enabled:
      filters !== null &&
      filters.materia_id !== '' &&
      filters.cohorte_id !== '',
  })
}

export function useCreateFecha() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: FechaAcademicaForm) => createFecha(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: fechasKeys.all })
    },
  })
}

export function useUpdateFecha() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string
      data: FechaAcademicaUpdateForm
    }) => updateFecha(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: fechasKeys.all })
    },
  })
}

export function useDeleteFecha() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteFecha(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: fechasKeys.all })
    },
  })
}
