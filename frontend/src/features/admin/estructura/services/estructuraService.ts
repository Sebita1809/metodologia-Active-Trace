/**
 * services/estructuraService.ts — API functions for estructura académica endpoints.
 *
 * All calls use the shared Axios instance from @/shared/services/api.
 * No business logic here — pure API wrappers returning typed responses.
 *
 * Base paths:
 *   Carreras:  /api/admin/carreras
 *   Cohortes:  /api/admin/cohortes
 *   Materias:  /api/admin/materias
 *
 * Note: update uses PATCH; delete returns 204.
 */

import { api } from '@/shared/services/api'
import type { Carrera, CarreraForm, Cohorte, CohorteForm, Materia, MateriaForm } from '../types'

const CARRERAS = '/api/admin/carreras'
const COHORTES = '/api/admin/cohortes'
const MATERIAS = '/api/admin/materias'

// ---------------------------------------------------------------------------
// Carreras
// ---------------------------------------------------------------------------

export async function getCarreras(): Promise<Carrera[]> {
  const { data } = await api.get<Carrera[]>(CARRERAS)
  return data
}

export async function createCarrera(data: CarreraForm): Promise<Carrera> {
  const { data: response } = await api.post<Carrera>(CARRERAS, data)
  return response
}

export async function updateCarrera(
  id: string,
  data: Partial<CarreraForm>,
): Promise<Carrera> {
  const { data: response } = await api.patch<Carrera>(`${CARRERAS}/${id}`, data)
  return response
}

export async function deleteCarrera(id: string): Promise<void> {
  await api.delete(`${CARRERAS}/${id}`)
}

// ---------------------------------------------------------------------------
// Cohortes
// ---------------------------------------------------------------------------

export async function getCohortes(carrera_id?: string): Promise<Cohorte[]> {
  const { data } = await api.get<Cohorte[]>(COHORTES, {
    params: carrera_id ? { carrera_id } : undefined,
  })
  return data
}

export async function createCohorte(data: CohorteForm): Promise<Cohorte> {
  const { data: response } = await api.post<Cohorte>(COHORTES, data)
  return response
}

export async function updateCohorte(
  id: string,
  data: Partial<CohorteForm>,
): Promise<Cohorte> {
  const { data: response } = await api.patch<Cohorte>(`${COHORTES}/${id}`, data)
  return response
}

export async function deleteCohorte(id: string): Promise<void> {
  await api.delete(`${COHORTES}/${id}`)
}

// ---------------------------------------------------------------------------
// Materias
// ---------------------------------------------------------------------------

export async function getMaterias(): Promise<Materia[]> {
  const { data } = await api.get<Materia[]>(MATERIAS)
  return data
}

export async function createMateria(data: MateriaForm): Promise<Materia> {
  const { data: response } = await api.post<Materia>(MATERIAS, data)
  return response
}

export async function updateMateria(
  id: string,
  data: Partial<MateriaForm>,
): Promise<Materia> {
  const { data: response } = await api.patch<Materia>(`${MATERIAS}/${id}`, data)
  return response
}

export async function deleteMateria(id: string): Promise<void> {
  await api.delete(`${MATERIAS}/${id}`)
}
