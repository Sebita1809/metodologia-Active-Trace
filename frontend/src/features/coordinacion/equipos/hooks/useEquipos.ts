/**
 * hooks/useEquipos.ts — TanStack Query hooks for asignaciones and equipo operations.
 *
 * Hooks:
 *   useAsignaciones      — GET /api/asignaciones with filters
 *   useCreateAsignacion  — POST /api/asignaciones
 *   useCreateMasiva      — POST /api/equipos/asignaciones/masiva
 *   useClonarEquipo      — POST /api/equipos/asignaciones/clonar
 *   useUpdateVigencia    — PATCH /api/equipos/asignaciones/vigencia
 *   useBuscarUsuarios    — GET /api/equipos/usuarios/buscar
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  buscarUsuarios,
  clonarEquipo,
  createAsignacion,
  createMasiva,
  getAsignaciones,
  updateVigencia,
} from '../services/asignacionesService'
import type {
  AsignacionFilters,
  AsignacionMasivaRequest,
  ClonarEquipoRequest,
  CreateAsignacionRequest,
  ModificarVigenciaRequest,
} from '../types'

// Query key factories
export const asignacionesKeys = {
  all: ['coordinacion', 'asignaciones'] as const,
  list: (filters?: AsignacionFilters) =>
    [...asignacionesKeys.all, 'list', filters ?? {}] as const,
  usuarios: (q: string) => ['coordinacion', 'usuarios', q] as const,
}

// ---------------------------------------------------------------------------
// useAsignaciones — list with filters
// ---------------------------------------------------------------------------

export function useAsignaciones(filters?: AsignacionFilters) {
  return useQuery({
    queryKey: asignacionesKeys.list(filters),
    queryFn: () => getAsignaciones(filters),
  })
}

// ---------------------------------------------------------------------------
// useCreateAsignacion — individual create
// ---------------------------------------------------------------------------

export function useCreateAsignacion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateAsignacionRequest) => createAsignacion(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: asignacionesKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useCreateMasiva — bulk assignment
// ---------------------------------------------------------------------------

export function useCreateMasiva() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: AsignacionMasivaRequest) => createMasiva(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: asignacionesKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useClonarEquipo — clone team to new cohorte
// ---------------------------------------------------------------------------

export function useClonarEquipo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ClonarEquipoRequest) => clonarEquipo(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: asignacionesKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useUpdateVigencia — bulk update dates
// ---------------------------------------------------------------------------

export function useUpdateVigencia() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ModificarVigenciaRequest) => updateVigencia(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: asignacionesKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useBuscarUsuarios — autocomplete for docentes
// ---------------------------------------------------------------------------

export function useBuscarUsuarios(q: string) {
  return useQuery({
    queryKey: asignacionesKeys.usuarios(q),
    queryFn: () => buscarUsuarios(q),
    enabled: q.length >= 2,
  })
}
