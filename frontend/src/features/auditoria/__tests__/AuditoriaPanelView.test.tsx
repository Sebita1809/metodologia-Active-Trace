/**
 * __tests__/AuditoriaPanelView.test.tsx — Task 12.6
 *
 * Tests for AuditoriaPanelView:
 *   - panel vacío con estado informativo
 *   - COORDINADOR no ve tab "Log completo"
 *   - ADMIN sí ve tab "Log completo"
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { AuditoriaPage } from '../pages/AuditoriaPage'

const EMPTY_ACCIONES = { items: [] }
const EMPTY_COMUNICACIONES = { items: [] }
const EMPTY_INTERACCIONES = { items: [] }
const EMPTY_ULTIMAS = { items: [] }

function setupMocks() {
  server.use(
    http.get('http://localhost:8000/api/auditoria/panel/acciones-por-dia', () =>
      HttpResponse.json(EMPTY_ACCIONES),
    ),
    http.get('http://localhost:8000/api/auditoria/panel/comunicaciones-por-docente', () =>
      HttpResponse.json(EMPTY_COMUNICACIONES),
    ),
    http.get('http://localhost:8000/api/auditoria/panel/interacciones-docente-materia', () =>
      HttpResponse.json(EMPTY_INTERACCIONES),
    ),
    http.get('http://localhost:8000/api/auditoria/panel/ultimas-acciones', () =>
      HttpResponse.json(EMPTY_ULTIMAS),
    ),
  )
}

describe('AuditoriaPage', () => {
  it('12.6a: panel vacío muestra estado informativo (sin datos)', async () => {
    setupMocks()
    const jwt = makeFakeJwt({ roles: ['COORDINADOR'] })
    tokenStorage.setTokens(jwt, jwt)

    renderWithProviders(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getByText(/acciones por día/i)).toBeInTheDocument()
    })

    // Empty chart message should be visible
    expect(screen.getByText(/sin datos en el rango seleccionado/i)).toBeInTheDocument()
  })

  it('12.6b: COORDINADOR does NOT see "Log completo" tab', async () => {
    setupMocks()
    const jwt = makeFakeJwt({ roles: ['COORDINADOR'] })
    tokenStorage.setTokens(jwt, jwt)

    renderWithProviders(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getByText(/acciones por día/i)).toBeInTheDocument()
    })

    expect(screen.queryByRole('button', { name: /log completo/i })).not.toBeInTheDocument()
  })

  it('12.6c: ADMIN sees "Log completo" tab', async () => {
    setupMocks()
    const jwt = makeFakeJwt({ roles: ['ADMIN'] })
    tokenStorage.setTokens(jwt, jwt)

    renderWithProviders(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getByText(/acciones por día/i)).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: /log completo/i })).toBeInTheDocument()
  })
})
