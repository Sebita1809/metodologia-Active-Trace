/**
 * __tests__/AprobacionComunicacionesPage.test.tsx
 *
 * Tests for task 13.6 — AprobacionComunicacionesPage:
 *   - empty state when no pending lotes
 *   - approve lote updates state
 *   - cancel lote requires confirmation dialog
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { AprobacionComunicacionesPage } from '../comunicaciones/components/AprobacionComunicacionesPage'

const COM_URL = 'http://localhost:8000/api/comunicaciones'
const APROBAR_URL = 'http://localhost:8000/api/comunicaciones/aprobar'
const CANCELAR_URL = 'http://localhost:8000/api/comunicaciones/cancelar'

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['COORDINADOR'] })
  tokenStorage.setTokens(jwt, jwt)
}

const LOTE_ITEM = {
  id: 'com-1',
  tenant_id: 'tenant-abc',
  enviado_por: 'user-doc-1',
  materia_id: 'mat-1',
  destinatario: 'alumno@email.com',
  asunto: 'Aviso importante',
  cuerpo: 'Cuerpo del mensaje',
  estado: 'Pendiente',
  lote_id: 'lote-abc',
  enviado_at: null,
  aprobado_at: null,
  aprobado_por: null,
  created_at: '2025-01-01T00:00:00Z',
}

describe('AprobacionComunicacionesPage', () => {
  it('13.6a: shows empty state when no pending lotes', async () => {
    setupAuth()
    server.use(
      http.get(COM_URL, () => HttpResponse.json([])),
    )

    renderWithProviders(<AprobacionComunicacionesPage />)

    await waitFor(() => {
      expect(screen.getByText(/sin comunicaciones pendientes/i)).toBeInTheDocument()
    })
  })

  it('13.6b: shows lote in table when there are pending items', async () => {
    setupAuth()
    server.use(
      http.get(COM_URL, () => HttpResponse.json([LOTE_ITEM])),
    )

    renderWithProviders(<AprobacionComunicacionesPage />)

    await waitFor(() => {
      expect(screen.getByText('user-doc-1')).toBeInTheDocument()
      expect(screen.getByText('1')).toBeInTheDocument() // cantidad destinatarios
    })
  })

  it('13.6c: approve lote calls POST /aprobar', async () => {
    setupAuth()
    let aprobarCalled = false

    server.use(
      http.get(COM_URL, () => HttpResponse.json([LOTE_ITEM])),
      http.post(APROBAR_URL, async () => {
        aprobarCalled = true
        return HttpResponse.json({ actualizados: 1 })
      }),
    )

    renderWithProviders(<AprobacionComunicacionesPage />)

    const aprobarBtn = await screen.findByRole('button', { name: /aprobar/i })
    await userEvent.click(aprobarBtn)

    await waitFor(() => {
      expect(aprobarCalled).toBe(true)
    })
  })

  it('13.6d: cancel shows confirmation dialog before calling API', async () => {
    setupAuth()
    let cancelarCalled = false

    server.use(
      http.get(COM_URL, () => HttpResponse.json([LOTE_ITEM])),
      http.post(CANCELAR_URL, async () => {
        cancelarCalled = true
        return HttpResponse.json({ cancelados: 1 })
      }),
    )

    renderWithProviders(<AprobacionComunicacionesPage />)

    const cancelarBtn = await screen.findByRole('button', { name: /^cancelar$/i })
    await userEvent.click(cancelarBtn)

    // Confirmation dialog should appear
    await waitFor(() => {
      expect(screen.getByText(/confirmar cancelación/i)).toBeInTheDocument()
      expect(screen.getByText(/1 mensaje\(s\)/i)).toBeInTheDocument()
    })

    // API should NOT be called yet
    expect(cancelarCalled).toBe(false)

    // Confirm cancellation
    const confirmarBtn = screen.getByRole('button', { name: /confirmar cancelación/i })
    await userEvent.click(confirmarBtn)

    await waitFor(() => {
      expect(cancelarCalled).toBe(true)
    })
  })

  it('13.6e: dismiss dialog keeps lote in pending state', async () => {
    setupAuth()
    let cancelarCalled = false

    server.use(
      http.get(COM_URL, () => HttpResponse.json([LOTE_ITEM])),
      http.post(CANCELAR_URL, async () => {
        cancelarCalled = true
        return HttpResponse.json({ cancelados: 1 })
      }),
    )

    renderWithProviders(<AprobacionComunicacionesPage />)

    const cancelarBtn = await screen.findByRole('button', { name: /^cancelar$/i })
    await userEvent.click(cancelarBtn)

    await waitFor(() => {
      expect(screen.getByText(/confirmar cancelación/i)).toBeInTheDocument()
    })

    // Dismiss dialog
    const mantenerBtn = screen.getByRole('button', { name: /mantener pendiente/i })
    await userEvent.click(mantenerBtn)

    expect(cancelarCalled).toBe(false)
    // Dialog should be gone
    expect(screen.queryByText(/confirmar cancelación/i)).not.toBeInTheDocument()
  })
})
