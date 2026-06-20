/**
 * __tests__/AnalisisViews.test.tsx
 *
 * Tests for tasks 8.1, 8.3, 8.4, 8.5 — Analisis sub-views.
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { TablaAtrasados } from '../components/analisis/TablaAtrasados'
import { RankingView } from '../components/analisis/RankingView'
import { NotasFinalesView } from '../components/analisis/NotasFinalesView'
import { ReporteView } from '../components/analisis/ReporteView'

const ASIG_ID = 'asig-analisis-1'
const BASE = 'http://localhost:8000/api/v1/analisis'

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['PROFESOR'] })
  tokenStorage.setTokens(jwt, jwt)
}

const ATRASADOS_RESPONSE = {
  atrasados: [
    {
      alumno_id: 'alu-1',
      nombre: 'Juan',
      apellidos: 'Pérez',
      actividades_faltantes: ['Tarea 3'],
      actividades_reprobadas: [],
    },
  ],
  sin_padron: false,
}

const RANKING_RESPONSE = {
  items: [
    { alumno_id: 'alu-1', nombre: 'Ana', apellidos: 'López', aprobadas: 5 },
    { alumno_id: 'alu-2', nombre: 'Carlos', apellidos: 'Gómez', aprobadas: 3 },
  ],
}

const NOTAS_RESPONSE = {
  items: [
    {
      alumno_id: 'alu-1',
      nombre: 'Ana',
      apellidos: 'López',
      aprobadas: 5,
      total_actividades: 6,
      porcentaje_aprobacion: 83.33,
    },
  ],
}

const REPORTE_RESPONSE = {
  total_alumnos: 20,
  total_atrasados: 5,
  pct_aprobacion_general: 75.0,
  total_actividades: 6,
  tiene_datos: true,
}

describe('TablaAtrasados', () => {
  it('8.1: renders atrasados data from backend', async () => {
    setupAuth()
    server.use(
      http.get(`${BASE}/atrasados`, () => HttpResponse.json(ATRASADOS_RESPONSE)),
    )
    renderWithProviders(<TablaAtrasados asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText('Juan')).toBeInTheDocument()
      expect(screen.getByText('Tarea 3')).toBeInTheDocument()
    })
  })

  it('8.1: shows "sin atrasados" state with empty list', async () => {
    setupAuth()
    server.use(
      http.get(`${BASE}/atrasados`, () =>
        HttpResponse.json({ atrasados: [], sin_padron: false }),
      ),
    )
    renderWithProviders(<TablaAtrasados asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText(/sin alumnos atrasados/i)).toBeInTheDocument()
    })
  })
})

describe('RankingView', () => {
  it('8.3: shows ranking ordered by aprobadas', async () => {
    setupAuth()
    server.use(
      http.get(`${BASE}/ranking`, () => HttpResponse.json(RANKING_RESPONSE)),
    )
    renderWithProviders(<RankingView asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText('Ana')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
    })
  })
})

describe('NotasFinalesView', () => {
  it('8.4: shows final grades per student', async () => {
    setupAuth()
    server.use(
      http.get(`${BASE}/notas-finales`, () => HttpResponse.json(NOTAS_RESPONSE)),
    )
    renderWithProviders(<NotasFinalesView asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText('Ana')).toBeInTheDocument()
      // Percentage should appear
      expect(screen.getByText(/83/)).toBeInTheDocument()
    })
  })
})

describe('ReporteView', () => {
  it('8.5: shows report metrics when data exists', async () => {
    setupAuth()
    server.use(
      http.get(`${BASE}/reporte`, () => HttpResponse.json(REPORTE_RESPONSE)),
    )
    renderWithProviders(<ReporteView asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText('20')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
    })
  })

  it('8.5: shows informative state when no data', async () => {
    setupAuth()
    server.use(
      http.get(`${BASE}/reporte`, () =>
        HttpResponse.json({
          total_alumnos: 0,
          total_atrasados: 0,
          pct_aprobacion_general: 0,
          total_actividades: 0,
          tiene_datos: false,
        }),
      ),
    )
    renderWithProviders(<ReporteView asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText(/sin datos/i)).toBeInTheDocument()
    })
  })
})
