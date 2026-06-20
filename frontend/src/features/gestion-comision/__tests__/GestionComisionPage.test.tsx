/**
 * __tests__/GestionComisionPage.test.tsx
 *
 * Tests for the GestionComisionPage orchestration and selector (tasks 4.1–4.5).
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { GestionComisionPage } from '../pages/GestionComisionPage'

// Fake asignaciones list
const FAKE_ASIGNACIONES = [
  {
    id: 'asig-1',
    tenant_id: 'tenant-abc',
    usuario_id: 'user-123',
    rol: 'PROFESOR',
    materia_id: 'mat-1',
    carrera_id: 'car-1',
    cohorte_id: 'coh-1',
    comisiones: ['C1'],
    responsable_id: null,
    desde: '2024-01-01',
    hasta: null,
    estado_vigencia: 'Vigente',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
]

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['PROFESOR'], sub: 'user-123' })
  tokenStorage.setTokens(jwt, jwt)
}

describe('GestionComisionPage', () => {
  it('4.1: shows informative state without comision selected and does not fire academic data requests', async () => {
    setupAuth()

    // Mock asignaciones endpoint — return list with one item
    server.use(
      http.get('http://localhost:8000/api/asignaciones', () =>
        HttpResponse.json(FAKE_ASIGNACIONES),
      ),
    )

    // Spy to detect forbidden requests
    const atrasadosCalled = vi.fn()
    server.use(
      http.get('http://localhost:8000/api/v1/analisis/atrasados', () => {
        atrasadosCalled()
        return HttpResponse.json({ atrasados: [], sin_padron: false })
      }),
    )

    renderWithProviders(<GestionComisionPage />)

    // Should show the selector prompt without data
    expect(
      await screen.findByText(/seleccioná una comisión/i),
    ).toBeInTheDocument()

    // Academic data requests must NOT fire without a selection
    expect(atrasadosCalled).not.toHaveBeenCalled()
  })

  it('4.3: sub-views show "sin datos" state when comision has no imported data', async () => {
    setupAuth()

    server.use(
      http.get('http://localhost:8000/api/asignaciones', () =>
        HttpResponse.json(FAKE_ASIGNACIONES),
      ),
      http.get('http://localhost:8000/api/v1/analisis/reporte', () =>
        HttpResponse.json({
          total_alumnos: 0,
          total_atrasados: 0,
          pct_aprobacion_general: 0,
          total_actividades: 0,
          tiene_datos: false,
        }),
      ),
    )

    renderWithProviders(<GestionComisionPage />)

    // Select the comision
    const select = await screen.findByRole('combobox', { name: /comisión/i })
    await userEvent.selectOptions(select, 'asig-1')

    // Should show "sin datos" informative state
    await waitFor(() => {
      expect(screen.getByText(/sin datos/i)).toBeInTheDocument()
    })
  })

  it('4.5: shows access denied state when backend returns 403', async () => {
    setupAuth()

    server.use(
      http.get('http://localhost:8000/api/asignaciones', () =>
        HttpResponse.json(FAKE_ASIGNACIONES),
      ),
      http.get('http://localhost:8000/api/v1/analisis/reporte', () =>
        HttpResponse.json({ detail: 'Forbidden' }, { status: 403 }),
      ),
    )

    renderWithProviders(<GestionComisionPage />)

    const select = await screen.findByRole('combobox', { name: /comisión/i })
    await userEvent.selectOptions(select, 'asig-1')

    await waitFor(() => {
      expect(screen.getByText(/acceso denegado/i)).toBeInTheDocument()
    })
  })
})
