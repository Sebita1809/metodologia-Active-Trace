/**
 * __tests__/MonitorSeguimientoExtendido.test.tsx
 *
 * Tests for task 13.7 — MonitorSeguimiento extension (C-23 F2.9):
 *   - date filters visible for COORDINADOR
 *   - date filters hidden for PROFESOR
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { MonitorSeguimiento } from '@/features/gestion-comision/components/seguimiento/MonitorSeguimiento'

const REPORTE_URL = 'http://localhost:8000/api/v1/analisis/reporte'
const NOTAS_URL = 'http://localhost:8000/api/v1/analisis/notas-finales'

const REPORTE_WITH_DATA = {
  total_alumnos: 2,
  total_atrasados: 0,
  pct_aprobacion_general: 80,
  total_actividades: 5,
  tiene_datos: true,
}

const NOTAS_RESPONSE = {
  items: [
    {
      alumno_id: 'alu-1',
      nombre: 'Ana',
      apellidos: 'García',
      aprobadas: 4,
      total_actividades: 5,
      porcentaje_aprobacion: 80,
    },
  ],
}

describe('MonitorSeguimiento — extended date filters (C-23 F2.9)', () => {
  it('13.7a: date filters ARE visible for COORDINADOR', async () => {
    const jwt = makeFakeJwt({ roles: ['COORDINADOR'] })
    tokenStorage.setTokens(jwt, jwt)

    server.use(
      http.get(REPORTE_URL, () => HttpResponse.json(REPORTE_WITH_DATA)),
      http.get(NOTAS_URL, () => HttpResponse.json(NOTAS_RESPONSE)),
    )

    renderWithProviders(<MonitorSeguimiento asignacionId="asig-1" />)

    await waitFor(() => {
      expect(screen.getByText('Ana')).toBeInTheDocument()
    })

    // Date filters must be visible
    expect(screen.getByLabelText(/desde/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/hasta/i)).toBeInTheDocument()
  })

  it('13.7b: date filters ARE visible for ADMIN', async () => {
    const jwt = makeFakeJwt({ roles: ['ADMIN'] })
    tokenStorage.setTokens(jwt, jwt)

    server.use(
      http.get(REPORTE_URL, () => HttpResponse.json(REPORTE_WITH_DATA)),
      http.get(NOTAS_URL, () => HttpResponse.json(NOTAS_RESPONSE)),
    )

    renderWithProviders(<MonitorSeguimiento asignacionId="asig-1" />)

    await waitFor(() => {
      expect(screen.getByText('Ana')).toBeInTheDocument()
    })

    expect(screen.getByLabelText(/desde/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/hasta/i)).toBeInTheDocument()
  })

  it('13.7c: date filters are NOT visible for PROFESOR', async () => {
    const jwt = makeFakeJwt({ roles: ['PROFESOR'] })
    tokenStorage.setTokens(jwt, jwt)

    server.use(
      http.get(REPORTE_URL, () => HttpResponse.json(REPORTE_WITH_DATA)),
      http.get(NOTAS_URL, () => HttpResponse.json(NOTAS_RESPONSE)),
    )

    renderWithProviders(<MonitorSeguimiento asignacionId="asig-1" />)

    await waitFor(() => {
      expect(screen.getByText('Ana')).toBeInTheDocument()
    })

    // Date filters must NOT be visible
    expect(screen.queryByLabelText(/desde/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/hasta/i)).not.toBeInTheDocument()
  })

  it('13.7d: date filters are NOT visible for TUTOR', async () => {
    const jwt = makeFakeJwt({ roles: ['TUTOR'] })
    tokenStorage.setTokens(jwt, jwt)

    server.use(
      http.get(REPORTE_URL, () => HttpResponse.json(REPORTE_WITH_DATA)),
      http.get(NOTAS_URL, () => HttpResponse.json(NOTAS_RESPONSE)),
    )

    renderWithProviders(<MonitorSeguimiento asignacionId="asig-1" />)

    await waitFor(() => {
      expect(screen.getByText('Ana')).toBeInTheDocument()
    })

    expect(screen.queryByLabelText(/desde/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/hasta/i)).not.toBeInTheDocument()
  })
})
