/**
 * __tests__/ComunicacionView.test.tsx
 *
 * Tests for tasks 10.1, 10.3, 10.5, 10.7 — Comunicación a atrasados con tracking.
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { ComunicacionView } from '../components/comunicacion/ComunicacionView'

const ASIG_ID = 'asig-com-1'
const MAT_ID = 'mat-com-1'
const ATRASADOS_URL = 'http://localhost:8000/api/v1/analisis/atrasados'
const PREVIEW_URL = 'http://localhost:8000/api/comunicaciones/preview'
const ENCOLAR_URL = 'http://localhost:8000/api/comunicaciones'
const COLA_URL = 'http://localhost:8000/api/comunicaciones'
const UMBRAL_URL = 'http://localhost:8000/api/calificaciones/umbral'

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
      actividades_faltantes: ['Tarea 1'],
      actividades_reprobadas: [],
    },
    {
      alumno_id: 'alu-2',
      nombre: 'María',
      apellidos: 'Gómez',
      actividades_faltantes: ['Tarea 2'],
      actividades_reprobadas: [],
    },
  ],
  sin_padron: false,
}

const UMBRAL_RESPONSE = {
  id: 'umb-1',
  asignacion_id: ASIG_ID,
  materia_id: MAT_ID,
  umbral_pct: 60,
  valores_aprobatorios: ['Satisfactorio'],
}

describe('ComunicacionView', () => {
  it('10.1: blocks continue when no recipients selected', async () => {
    setupAuth()
    server.use(
      http.get(ATRASADOS_URL, () => HttpResponse.json(ATRASADOS_RESPONSE)),
      http.get(UMBRAL_URL, () => HttpResponse.json(UMBRAL_RESPONSE)),
    )

    renderWithProviders(<ComunicacionView asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText('Juan')).toBeInTheDocument()
    })

    // Continue button should be disabled without selections
    const continueBtn = screen.getByRole('button', { name: /continuar/i })
    expect(continueBtn).toBeDisabled()
  })

  it('10.1: selecting recipients enables continue button', async () => {
    setupAuth()
    server.use(
      http.get(ATRASADOS_URL, () => HttpResponse.json(ATRASADOS_RESPONSE)),
      http.get(UMBRAL_URL, () => HttpResponse.json(UMBRAL_RESPONSE)),
    )

    renderWithProviders(<ComunicacionView asignacionId={ASIG_ID} />)

    await waitFor(() => {
      expect(screen.getByText('Juan')).toBeInTheDocument()
    })

    const checkbox = screen.getByLabelText(/seleccionar Juan/i)
    await userEvent.click(checkbox)

    const continueBtn = screen.getByRole('button', { name: /continuar/i })
    expect(continueBtn).not.toBeDisabled()
  })

  it('10.3: preview shows subject/body per recipient without enqueueing', async () => {
    setupAuth()
    server.use(
      http.get(ATRASADOS_URL, () => HttpResponse.json(ATRASADOS_RESPONSE)),
      http.get(UMBRAL_URL, () => HttpResponse.json(UMBRAL_RESPONSE)),
      http.post(PREVIEW_URL, () =>
        HttpResponse.json({
          resultados: [
            {
              email: 'juan@test.com',
              asunto_renderizado: 'Alerta: actividades pendientes',
              cuerpo_renderizado: 'Hola Juan, tenés actividades pendientes.',
            },
          ],
        }),
      ),
    )

    renderWithProviders(<ComunicacionView asignacionId={ASIG_ID} />)

    // Select Juan
    await waitFor(() => screen.getByText('Juan'))
    await userEvent.click(screen.getByLabelText(/seleccionar Juan/i))
    await userEvent.click(screen.getByRole('button', { name: /continuar/i }))

    // Fill draft form
    const asuntoInput = await screen.findByLabelText(/asunto/i)
    await userEvent.type(asuntoInput, 'Alerta: actividades pendientes')

    const cuerpoInput = screen.getByLabelText(/cuerpo/i)
    await userEvent.type(cuerpoInput, 'Hola {{nombre}}, tenés actividades pendientes.')

    await userEvent.click(screen.getByRole('button', { name: /previsualizar/i }))

    await waitFor(() => {
      expect(screen.getByText('Alerta: actividades pendientes')).toBeInTheDocument()
      expect(screen.getByText(/actividades pendientes/i)).toBeInTheDocument()
    })
  })

  it('10.5: confirming enqueues the lote and receives lote_id', async () => {
    setupAuth()

    let enqueueCalled = false
    const LOTE_ID = 'lote-abc-123'

    server.use(
      http.get(ATRASADOS_URL, () => HttpResponse.json(ATRASADOS_RESPONSE)),
      http.get(UMBRAL_URL, () => HttpResponse.json(UMBRAL_RESPONSE)),
      http.post(PREVIEW_URL, () =>
        HttpResponse.json({
          resultados: [
            {
              email: 'juan@test.com',
              asunto_renderizado: 'Asunto',
              cuerpo_renderizado: 'Cuerpo',
            },
          ],
        }),
      ),
      http.post(ENCOLAR_URL, () => {
        enqueueCalled = true
        return HttpResponse.json({ lote_id: LOTE_ID, cantidad: 1 }, { status: 201 })
      }),
      http.get(COLA_URL, ({ request }) => {
        const url = new URL(request.url)
        if (url.searchParams.get('lote_id') === LOTE_ID) {
          return HttpResponse.json([
            {
              id: 'com-1',
              tenant_id: 'tenant-abc',
              enviado_por: 'user-123',
              materia_id: MAT_ID,
              destinatario: 'juan@test.com',
              asunto: 'Asunto',
              cuerpo: 'Cuerpo',
              estado: 'Pendiente',
              lote_id: LOTE_ID,
              enviado_at: null,
              aprobado_at: null,
              aprobado_por: null,
              created_at: '2024-01-01T00:00:00Z',
            },
          ])
        }
        return HttpResponse.json([])
      }),
    )

    renderWithProviders(<ComunicacionView asignacionId={ASIG_ID} />)

    await waitFor(() => screen.getByText('Juan'))
    await userEvent.click(screen.getByLabelText(/seleccionar Juan/i))
    await userEvent.click(screen.getByRole('button', { name: /continuar/i }))

    const asuntoInput = await screen.findByLabelText(/asunto/i)
    await userEvent.type(asuntoInput, 'Asunto')
    const cuerpoInput = screen.getByLabelText(/cuerpo/i)
    await userEvent.type(cuerpoInput, 'Cuerpo')

    await userEvent.click(screen.getByRole('button', { name: /previsualizar/i }))
    await waitFor(() => screen.getByText('Asunto'))

    await userEvent.click(screen.getByRole('button', { name: /confirmar envío/i }))

    await waitFor(() => {
      expect(enqueueCalled).toBe(true)
    })

    // Should show tracking panel with Pendiente state
    await waitFor(() => {
      expect(screen.getByText(/pendiente/i)).toBeInTheDocument()
    })
  })

  it('10.7: tracking stops polling when all messages reach terminal state', async () => {
    setupAuth()

    const LOTE_ID = 'lote-terminal'
    let pollCount = 0

    server.use(
      http.get(ATRASADOS_URL, () => HttpResponse.json(ATRASADOS_RESPONSE)),
      http.get(UMBRAL_URL, () => HttpResponse.json(UMBRAL_RESPONSE)),
      http.post(PREVIEW_URL, () =>
        HttpResponse.json({
          resultados: [
            { email: 'juan@test.com', asunto_renderizado: 'A', cuerpo_renderizado: 'B' },
          ],
        }),
      ),
      http.post(ENCOLAR_URL, () =>
        HttpResponse.json({ lote_id: LOTE_ID, cantidad: 1 }, { status: 201 }),
      ),
      http.get(COLA_URL, ({ request }) => {
        const url = new URL(request.url)
        if (url.searchParams.get('lote_id') === LOTE_ID) {
          pollCount++
          // Return Enviado (terminal) right away
          return HttpResponse.json([
            {
              id: 'com-1',
              tenant_id: 'tenant-abc',
              enviado_por: 'user-123',
              materia_id: MAT_ID,
              destinatario: 'juan@test.com',
              asunto: 'A',
              cuerpo: 'B',
              estado: 'Enviado',
              lote_id: LOTE_ID,
              enviado_at: '2024-01-01T00:00:00Z',
              aprobado_at: null,
              aprobado_por: null,
              created_at: '2024-01-01T00:00:00Z',
            },
          ])
        }
        return HttpResponse.json([])
      }),
    )

    renderWithProviders(<ComunicacionView asignacionId={ASIG_ID} />)

    await waitFor(() => screen.getByText('Juan'))
    await userEvent.click(screen.getByLabelText(/seleccionar Juan/i))
    await userEvent.click(screen.getByRole('button', { name: /continuar/i }))

    const asuntoInput = await screen.findByLabelText(/asunto/i)
    await userEvent.type(asuntoInput, 'A')
    const cuerpoInput = screen.getByLabelText(/cuerpo/i)
    await userEvent.type(cuerpoInput, 'B')

    await userEvent.click(screen.getByRole('button', { name: /previsualizar/i }))
    await waitFor(() => screen.getByText('A'))

    await userEvent.click(screen.getByRole('button', { name: /confirmar envío/i }))

    // Wait for Enviado terminal state to appear
    await waitFor(() => {
      expect(screen.getByText(/enviado/i)).toBeInTheDocument()
    })

    // Poll count should be small (1-2) because terminal state stops polling
    expect(pollCount).toBeLessThanOrEqual(3)
  })
})
