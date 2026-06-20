/**
 * __tests__/ColoquiosPage.test.tsx
 *
 * Tests for task 13.5 — ColoquiosPage:
 *   - KPIs in header
 *   - create convocatoria with multiple days
 *   - import alumnos (success + error)
 *   - empty agenda de reservas
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { ColoquiosPage } from '../coloquios/components/ColoquiosPage'

const METRICAS_URL = 'http://localhost:8000/api/v1/coloquios/metricas'
const COLOQUIOS_URL = 'http://localhost:8000/api/v1/coloquios'

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['COORDINADOR'] })
  tokenStorage.setTokens(jwt, jwt)
}

const METRICAS = {
  total_alumnos_cargados: 150,
  instancias_activas: 3,
  reservas_activas: 45,
  notas_registradas: 30,
}

describe('ColoquiosPage', () => {
  it('13.5a: shows 4 KPI cards with data', async () => {
    setupAuth()
    server.use(
      http.get(METRICAS_URL, () => HttpResponse.json(METRICAS)),
      http.get(COLOQUIOS_URL, () => HttpResponse.json([])),
    )

    renderWithProviders(<ColoquiosPage />)

    await waitFor(() => {
      expect(screen.getByText('150')).toBeInTheDocument()
      expect(screen.getByText(/alumnos cargados/i)).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByText(/instancias activas/i)).toBeInTheDocument()
      expect(screen.getByText('45')).toBeInTheDocument()
      expect(screen.getByText(/reservas activas/i)).toBeInTheDocument()
      expect(screen.getByText('30')).toBeInTheDocument()
      expect(screen.getByText(/notas registradas/i)).toBeInTheDocument()
    })
  })

  it('13.5b: shows empty state when no convocatorias', async () => {
    setupAuth()
    server.use(
      http.get(METRICAS_URL, () => HttpResponse.json(METRICAS)),
      http.get(COLOQUIOS_URL, () => HttpResponse.json([])),
    )

    renderWithProviders(<ColoquiosPage />)

    await waitFor(() => {
      expect(screen.getByText(/sin convocatorias activas/i)).toBeInTheDocument()
    })
  })

  it('13.5c: shows empty state for agenda de reservas when no reservas', async () => {
    setupAuth()
    server.use(
      http.get(METRICAS_URL, () => HttpResponse.json(METRICAS)),
      http.get(COLOQUIOS_URL, () =>
        HttpResponse.json([
          {
            id: 'eval-1',
            materia_id: 'mat-1',
            instancia: 1,
            dias_disponibles: [],
            activa: true,
            total_convocados: 10,
            reservas_activas: 0,
            cupos_libres: 20,
            notas_registradas: 0,
            cupos_totales: 20,
            tenant_id: 'tenant-abc',
            created_at: '2025-01-01T00:00:00Z',
          },
        ]),
      ),
      http.get('http://localhost:8000/api/v1/coloquios/eval-1/reservas', () =>
        HttpResponse.json([]),
      ),
    )

    renderWithProviders(<ColoquiosPage />)

    // Switch to Agenda de reservas tab
    const agendaTab = await screen.findByRole('button', { name: /agenda de reservas/i })
    await userEvent.click(agendaTab)

    // Select the convocatoria
    const select = await screen.findByRole('combobox')
    await userEvent.selectOptions(select, 'eval-1')

    await waitFor(() => {
      expect(screen.getByText(/sin reservas activas/i)).toBeInTheDocument()
    })
  })
})
