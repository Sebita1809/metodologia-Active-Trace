/**
 * __tests__/MonitorSeguimiento.test.tsx
 *
 * Tests for tasks 9.1, 9.3 — Monitor de seguimiento filtrable.
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { MonitorSeguimiento } from '../components/seguimiento/MonitorSeguimiento'

const ASIG_ID = 'asig-monitor-1'
const REPORTE_URL = 'http://localhost:8000/api/v1/analisis/reporte'
const NOTAS_URL = 'http://localhost:8000/api/v1/analisis/notas-finales'

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['PROFESOR'] })
  tokenStorage.setTokens(jwt, jwt)
}

const NOTAS_RESPONSE = {
  items: [
    {
      alumno_id: 'alu-1',
      nombre: 'Ana',
      apellidos: 'García',
      aprobadas: 5,
      total_actividades: 6,
      porcentaje_aprobacion: 83.33,
    },
    {
      alumno_id: 'alu-2',
      nombre: 'Luis',
      apellidos: 'Martínez',
      aprobadas: 2,
      total_actividades: 6,
      porcentaje_aprobacion: 33.33,
    },
  ],
}

describe('MonitorSeguimiento', () => {
  it('9.1: shows activity status table when data exists', async () => {
    setupAuth()
    server.use(
      http.get(REPORTE_URL, () =>
        HttpResponse.json({
          total_alumnos: 2,
          total_atrasados: 1,
          pct_aprobacion_general: 58.33,
          total_actividades: 6,
          tiene_datos: true,
        }),
      ),
      http.get(NOTAS_URL, () => HttpResponse.json(NOTAS_RESPONSE)),
    )

    renderWithProviders(<MonitorSeguimiento asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText('Ana')).toBeInTheDocument()
      expect(screen.getByText('Luis')).toBeInTheDocument()
    })
  })

  it('9.1: shows "sin datos de seguimiento" when no data', async () => {
    setupAuth()
    server.use(
      http.get(REPORTE_URL, () =>
        HttpResponse.json({
          total_alumnos: 0,
          total_atrasados: 0,
          pct_aprobacion_general: 0,
          total_actividades: 0,
          tiene_datos: false,
        }),
      ),
      http.get(NOTAS_URL, () => HttpResponse.json({ items: [] })),
    )

    renderWithProviders(<MonitorSeguimiento asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText(/sin datos de seguimiento/i)).toBeInTheDocument()
    })
  })

  it('9.3: filtering by student name shows only matching rows', async () => {
    setupAuth()
    server.use(
      http.get(REPORTE_URL, () =>
        HttpResponse.json({
          total_alumnos: 2,
          total_atrasados: 0,
          pct_aprobacion_general: 58.33,
          total_actividades: 6,
          tiene_datos: true,
        }),
      ),
      http.get(NOTAS_URL, () => HttpResponse.json(NOTAS_RESPONSE)),
    )

    renderWithProviders(<MonitorSeguimiento asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText('Ana')).toBeInTheDocument()
    })

    const filtroInput = screen.getByPlaceholderText(/buscar alumno/i)
    await userEvent.type(filtroInput, 'Ana')

    await waitFor(() => {
      expect(screen.getByText('Ana')).toBeInTheDocument()
      expect(screen.queryByText('Luis')).not.toBeInTheDocument()
    })
  })

  it('9.3: filtering by minimum cumplido hides students below threshold', async () => {
    setupAuth()
    server.use(
      http.get(REPORTE_URL, () =>
        HttpResponse.json({
          total_alumnos: 2,
          total_atrasados: 1,
          pct_aprobacion_general: 58.33,
          total_actividades: 6,
          tiene_datos: true,
        }),
      ),
      http.get(NOTAS_URL, () => HttpResponse.json(NOTAS_RESPONSE)),
    )

    renderWithProviders(<MonitorSeguimiento asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText('Luis')).toBeInTheDocument()
    })

    const minInput = screen.getByLabelText(/mínimo cumplido/i)
    await userEvent.clear(minInput)
    await userEvent.type(minInput, '60')

    await waitFor(() => {
      // Ana (83.33%) should appear, Luis (33.33%) should not
      expect(screen.getByText('Ana')).toBeInTheDocument()
      expect(screen.queryByText('Luis')).not.toBeInTheDocument()
    })
  })
})
