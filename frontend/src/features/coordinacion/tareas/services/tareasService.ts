/**
 * services/tareasService.ts — API functions for tareas endpoints.
 *
 * Paths confirmed by reading backend/app/api/v1/routers/tareas.py:
 *   Base path: /api/v1/tareas (C-16 router)
 *   GET /mias           — tareas asignadas al usuario autenticado
 *   GET /              — todas las tareas del tenant (admin)
 *   PATCH /{id}/estado — cambiar estado
 *   PATCH /{id}/delegar — delegar tarea
 *   POST /{id}/comentarios — agregar comentario
 *   GET /{id}/comentarios  — listar comentarios
 *
 * No `any` allowed.
 */

import { api } from '@/shared/services/api'
import type {
  CambiarEstadoTareaRequest,
  ComentarioTarea,
  CrearTareaRequest,
  Tarea,
  TareaFilters,
} from '../types'

const BASE = '/api/v1/tareas'

// ---------------------------------------------------------------------------
// POST /api/v1/tareas — create tarea
// ---------------------------------------------------------------------------

export async function createTarea(body: CrearTareaRequest): Promise<Tarea> {
  const { data } = await api.post<Tarea>(BASE, body)
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/tareas/mias — tareas propias del usuario autenticado
// ---------------------------------------------------------------------------

export async function getMisTareas(): Promise<Tarea[]> {
  const { data } = await api.get<Tarea[]>(`${BASE}/mias`)
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/tareas — todas las tareas del tenant con filtros
// ---------------------------------------------------------------------------

export async function getTareas(filters?: TareaFilters): Promise<Tarea[]> {
  const { data } = await api.get<Tarea[]>(BASE, { params: filters })
  return data
}

// ---------------------------------------------------------------------------
// PATCH /api/v1/tareas/{id}/estado — cambiar estado de tarea
// ---------------------------------------------------------------------------

export async function updateEstadoTarea(
  id: string,
  body: CambiarEstadoTareaRequest,
): Promise<Tarea> {
  const { data } = await api.patch<Tarea>(`${BASE}/${id}/estado`, body)
  return data
}

// ---------------------------------------------------------------------------
// POST /api/v1/tareas/{id}/comentarios — agregar comentario
// ---------------------------------------------------------------------------

export async function addComentario(
  id: string,
  texto: string,
): Promise<ComentarioTarea> {
  const { data } = await api.post<ComentarioTarea>(`${BASE}/${id}/comentarios`, {
    texto,
  })
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/tareas/{id}/comentarios — listar comentarios
// ---------------------------------------------------------------------------

export async function getComentarios(id: string): Promise<ComentarioTarea[]> {
  const { data } = await api.get<ComentarioTarea[]>(`${BASE}/${id}/comentarios`)
  return data
}
