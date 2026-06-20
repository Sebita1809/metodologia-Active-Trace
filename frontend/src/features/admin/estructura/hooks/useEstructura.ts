/**
 * hooks/useEstructura.ts — TanStack Query hooks for estructura académica endpoints.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createCarrera,
  createCohorte,
  createMateria,
  deleteCarrera,
  deleteCohorte,
  deleteMateria,
  getCarreras,
  getCohortes,
  getMaterias,
  updateCarrera,
  updateCohorte,
  updateMateria,
} from '../services/estructuraService'
import type { CarreraForm, CohorteForm, MateriaForm } from '../types'

// Query key factories
export const estructuraKeys = {
  all: ['estructura'] as const,
  carreras: () => [...estructuraKeys.all, 'carreras'] as const,
  cohortes: (carrera_id?: string) =>
    [...estructuraKeys.all, 'cohortes', carrera_id] as const,
  materias: () => [...estructuraKeys.all, 'materias'] as const,
}

// ---------------------------------------------------------------------------
// Carrera hooks
// ---------------------------------------------------------------------------

export function useCarreras() {
  return useQuery({
    queryKey: estructuraKeys.carreras(),
    queryFn: getCarreras,
  })
}

export function useCreateCarrera() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CarreraForm) => createCarrera(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: estructuraKeys.carreras() })
    },
  })
}

export function useUpdateCarrera() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CarreraForm> }) =>
      updateCarrera(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: estructuraKeys.carreras() })
    },
  })
}

export function useDeleteCarrera() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteCarrera(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: estructuraKeys.carreras() })
    },
  })
}

// ---------------------------------------------------------------------------
// Cohorte hooks
// ---------------------------------------------------------------------------

export function useCohortes(carrera_id?: string) {
  return useQuery({
    queryKey: estructuraKeys.cohortes(carrera_id),
    queryFn: () => getCohortes(carrera_id),
  })
}

export function useCreateCohorte() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CohorteForm) => createCohorte(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: estructuraKeys.all })
    },
  })
}

export function useUpdateCohorte() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CohorteForm> }) =>
      updateCohorte(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: estructuraKeys.all })
    },
  })
}

export function useDeleteCohorte() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteCohorte(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: estructuraKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// Materia hooks
// ---------------------------------------------------------------------------

export function useMaterias() {
  return useQuery({
    queryKey: estructuraKeys.materias(),
    queryFn: getMaterias,
  })
}

export function useCreateMateria() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: MateriaForm) => createMateria(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: estructuraKeys.materias() })
    },
  })
}

export function useUpdateMateria() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MateriaForm> }) =>
      updateMateria(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: estructuraKeys.materias() })
    },
  })
}

export function useDeleteMateria() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteMateria(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: estructuraKeys.materias() })
    },
  })
}
