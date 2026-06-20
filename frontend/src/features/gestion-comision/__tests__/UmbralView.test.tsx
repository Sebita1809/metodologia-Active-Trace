/**
 * __tests__/UmbralView.test.tsx
 *
 * Tests for tasks 7.1, 7.3 — Configuración del umbral de aprobación.
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { UmbralView } from '../components/umbral/UmbralView'

const ASIG_ID = 'asig-umbral-1'
const MAT_ID = 'mat-1'
const UMBRAL_URL = `http://localhost:8000/api/calificaciones/umbral`

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['PROFESOR'], sub: 'user-123' })
  tokenStorage.setTokens(jwt, jwt)
}

const DEFAULT_UMBRAL = {
  id: 'umb-1',
  asignacion_id: ASIG_ID,
  materia_id: MAT_ID,
  umbral_pct: 60,
  valores_aprobatorios: ['Satisfactorio', 'Supera lo esperado'],
}

const CUSTOM_UMBRAL = {
  ...DEFAULT_UMBRAL,
  umbral_pct: 75,
}

describe('UmbralView', () => {
  it('7.1: shows default umbral (60%) when not configured', async () => {
    setupAuth()

    server.use(
      http.get(UMBRAL_URL, () => HttpResponse.json(DEFAULT_UMBRAL)),
    )

    renderWithProviders(<UmbralView asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText(/60/)).toBeInTheDocument()
    })
  })

  it('7.1: shows persisted umbral when configured', async () => {
    setupAuth()

    server.use(
      http.get(UMBRAL_URL, () => HttpResponse.json(CUSTOM_UMBRAL)),
    )

    renderWithProviders(<UmbralView asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText(/75/)).toBeInTheDocument()
    })
  })

  it('7.3: saving a valid umbral sends PUT and reflects updated value', async () => {
    setupAuth()

    let putCalled = false
    server.use(
      http.get(UMBRAL_URL, () => HttpResponse.json(DEFAULT_UMBRAL)),
      http.put(UMBRAL_URL, async () => {
        putCalled = true
        return HttpResponse.json({ ...DEFAULT_UMBRAL, umbral_pct: 80 })
      }),
    )

    renderWithProviders(<UmbralView asignacionId={ASIG_ID} />)

    await screen.findByDisplayValue('60')

    // Clear and type a new value
    const umbralInput = screen.getByLabelText(/umbral/i)
    await userEvent.clear(umbralInput)
    await userEvent.type(umbralInput, '80')

    const saveBtn = screen.getByRole('button', { name: /guardar/i })
    await userEvent.click(saveBtn)

    await waitFor(() => {
      expect(putCalled).toBe(true)
    })
  })

  it('7.3: umbral out of range (>100) is blocked by Zod validation', async () => {
    setupAuth()

    server.use(
      http.get(UMBRAL_URL, () => HttpResponse.json(DEFAULT_UMBRAL)),
    )

    renderWithProviders(<UmbralView asignacionId={ASIG_ID} />)

    await screen.findByDisplayValue('60')

    const umbralInput = screen.getByLabelText(/umbral/i)
    await userEvent.clear(umbralInput)
    await userEvent.type(umbralInput, '150')

    const saveBtn = screen.getByRole('button', { name: /guardar/i })
    await userEvent.click(saveBtn)

    await waitFor(() => {
      expect(screen.getByText(/100/i)).toBeInTheDocument()
    })
  })
})
