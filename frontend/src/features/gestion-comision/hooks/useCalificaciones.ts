/**
 * hooks/useCalificaciones.ts — TanStack Query hooks for calificaciones endpoints.
 *
 * Hooks:
 *   useImportPreview       — mutation for POST /preview (no persist)
 *   useConfirmImport       — mutation for POST /import (multipart)
 *   useFinalizacionPreview — mutation for POST /finalizacion-preview
 *   useCalificaciones      — query for GET / (list)
 *   useUmbral              — query for GET /umbral
 *   useUpsertUmbral        — mutation for PUT /umbral
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  confirmImport,
  getUmbral,
  listCalificaciones,
  previewFinalizacion,
  previewImport,
  upsertUmbral,
} from '../services/calificacionesService'
import type { UmbralMateriaUpsert } from '../types/calificaciones'

// Query key factories
export const calificacionesKeys = {
  all: ['calificaciones'] as const,
  list: (asignacionId: string) =>
    [...calificacionesKeys.all, 'list', asignacionId] as const,
  umbral: (asignacionId: string) =>
    [...calificacionesKeys.all, 'umbral', asignacionId] as const,
}

// ---------------------------------------------------------------------------
// useImportPreview — mutation (POST /preview, no side effects)
// ---------------------------------------------------------------------------

export function useImportPreview() {
  return useMutation({
    mutationFn: ({ file, asignacion_id }: { file: File; asignacion_id: string }) =>
      previewImport(file, asignacion_id),
  })
}

// ---------------------------------------------------------------------------
// useConfirmImport — mutation (POST /import, 201 on success)
// ---------------------------------------------------------------------------

export function useConfirmImport(asignacion_id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      file,
      actividades_seleccionadas,
    }: {
      file: File
      actividades_seleccionadas: string[]
    }) =>
      confirmImport(file, {
        asignacion_id,
        actividades_seleccionadas,
      }),
    onSuccess: () => {
      // Invalidate the calificaciones list and analysis data after a successful import
      void queryClient.invalidateQueries({
        queryKey: calificacionesKeys.list(asignacion_id),
      })
    },
  })
}

// ---------------------------------------------------------------------------
// useFinalizacionPreview — mutation (POST /finalizacion-preview)
// ---------------------------------------------------------------------------

export function useFinalizacionPreview() {
  return useMutation({
    mutationFn: ({ file, asignacion_id }: { file: File; asignacion_id: string }) =>
      previewFinalizacion(file, asignacion_id),
  })
}

// ---------------------------------------------------------------------------
// useCalificaciones — query (GET /)
// ---------------------------------------------------------------------------

export function useCalificaciones(asignacion_id: string | null) {
  return useQuery({
    queryKey: calificacionesKeys.list(asignacion_id ?? ''),
    queryFn: () => listCalificaciones(asignacion_id!),
    enabled: asignacion_id !== null,
  })
}

// ---------------------------------------------------------------------------
// useUmbral — query (GET /umbral)
// ---------------------------------------------------------------------------

export function useUmbral(asignacion_id: string | null) {
  return useQuery({
    queryKey: calificacionesKeys.umbral(asignacion_id ?? ''),
    queryFn: () => getUmbral(asignacion_id!),
    enabled: asignacion_id !== null,
  })
}

// ---------------------------------------------------------------------------
// useUpsertUmbral — mutation (PUT /umbral)
// ---------------------------------------------------------------------------

export function useUpsertUmbral(asignacion_id: string, materia_id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: UmbralMateriaUpsert) =>
      upsertUmbral(asignacion_id, materia_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: calificacionesKeys.umbral(asignacion_id),
      })
    },
  })
}
