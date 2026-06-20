/**
 * hooks/useGrillaSalarial.ts — TanStack Query hooks for grilla salarial endpoints.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createPlus,
  createSalarioBase,
  deletePlus,
  deleteSalarioBase,
  getPlus,
  getSalariosBase,
  updatePlus,
  updateSalarioBase,
} from '../services/grillaSalarialService'
import type { SalarioBaseForm, PlusForm } from '../types'

// Query key factories
export const grillaKeys = {
  all: ['grilla-salarial'] as const,
  bases: () => [...grillaKeys.all, 'bases'] as const,
  plus: () => [...grillaKeys.all, 'plus'] as const,
}

// ---------------------------------------------------------------------------
// Salario Base hooks
// ---------------------------------------------------------------------------

export function useSalariosBase() {
  return useQuery({
    queryKey: grillaKeys.bases(),
    queryFn: getSalariosBase,
  })
}

export function useCreateSalarioBase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: SalarioBaseForm) => createSalarioBase(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: grillaKeys.bases() })
    },
  })
}

export function useUpdateSalarioBase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SalarioBaseForm> }) =>
      updateSalarioBase(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: grillaKeys.bases() })
    },
  })
}

export function useDeleteSalarioBase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteSalarioBase(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: grillaKeys.bases() })
    },
  })
}

// ---------------------------------------------------------------------------
// Plus hooks
// ---------------------------------------------------------------------------

export function usePlus() {
  return useQuery({
    queryKey: grillaKeys.plus(),
    queryFn: getPlus,
  })
}

export function useCreatePlus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: PlusForm) => createPlus(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: grillaKeys.plus() })
    },
  })
}

export function useUpdatePlus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<PlusForm> }) =>
      updatePlus(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: grillaKeys.plus() })
    },
  })
}

export function useDeletePlus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deletePlus(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: grillaKeys.plus() })
    },
  })
}
