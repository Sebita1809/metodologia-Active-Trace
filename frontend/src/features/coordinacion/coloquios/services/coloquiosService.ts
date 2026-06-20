/**
 * services/coloquiosService.ts — API functions for coloquios endpoints.
 *
 * Paths confirmed by reading backend/app/api/v1/routers/coloquios.py:
 *   POST   /api/v1/coloquios                        → crear evaluacion
 *   GET    /api/v1/coloquios                        → listar con metricas
 *   GET    /api/v1/coloquios/metricas               → panel de metricas
 *   POST   /api/v1/coloquios/{id}/alumnos           → importar padron
 *   GET    /api/v1/coloquios/{id}/reservas          → listar agenda
 *   GET    /api/v1/coloquios/{id}/resultados        → listar resultados
 *
 * No `any` allowed.
 */

import { api } from '@/shared/services/api'
import type {
  CrearEvaluacionRequest,
  EvaluacionConMetricas,
  ImportarPadronResponse,
  MetricasColoquios,
  Reserva,
  ResultadoColoquio,
} from '../types'

const BASE = '/api/v1/coloquios'

// ---------------------------------------------------------------------------
// GET /api/v1/coloquios — list evaluaciones with metrics
// ---------------------------------------------------------------------------

export async function getEvaluaciones(): Promise<EvaluacionConMetricas[]> {
  const { data } = await api.get<EvaluacionConMetricas[]>(BASE)
  return data
}

// ---------------------------------------------------------------------------
// POST /api/v1/coloquios — create new evaluacion
// ---------------------------------------------------------------------------

export async function createEvaluacion(
  body: CrearEvaluacionRequest,
): Promise<EvaluacionConMetricas> {
  const { data } = await api.post<EvaluacionConMetricas>(BASE, body)
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/coloquios/metricas — KPIs panel
// ---------------------------------------------------------------------------

export async function getMetricas(): Promise<MetricasColoquios> {
  const { data } = await api.get<MetricasColoquios>(`${BASE}/metricas`)
  return data
}

// ---------------------------------------------------------------------------
// POST /api/v1/coloquios/{id}/alumnos — import padron
// ---------------------------------------------------------------------------

export async function importarAlumnos(
  evaluacionId: string,
  file: File,
): Promise<ImportarPadronResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<ImportarPadronResponse>(
    `${BASE}/${evaluacionId}/alumnos`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/coloquios/{id}/reservas — list reservas by evaluacion
// ---------------------------------------------------------------------------

export async function getReservas(evaluacionId: string): Promise<Reserva[]> {
  const { data } = await api.get<Reserva[]>(`${BASE}/${evaluacionId}/reservas`)
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/coloquios/{id}/resultados — list resultados by evaluacion
// ---------------------------------------------------------------------------

export async function getResultados(
  evaluacionId: string,
): Promise<ResultadoColoquio[]> {
  const { data } = await api.get<ResultadoColoquio[]>(
    `${BASE}/${evaluacionId}/resultados`,
  )
  return data
}
