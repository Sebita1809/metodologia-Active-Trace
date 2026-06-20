/**
 * __tests__/FinalizacionView.test.tsx
 *
 * Tests for tasks 6.1, 6.3 — Entregas sin corregir + export.
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { FinalizacionView } from '../components/import/FinalizacionView'

const ASIG_ID = 'asig-fin-1'
const FINALIZACION_URL = 'http://localhost:8000/api/calificaciones/finalizacion-preview'

const FINALIZACION_RESPONSE = {
  items: [
    { alumno_email: 'alumno@test.com', actividad: 'Tarea Final' },
    { alumno_email: 'otro@test.com', actividad: 'Tarea Final' },
  ],
}

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['PROFESOR'], sub: 'user-123' })
  tokenStorage.setTokens(jwt, jwt)
}

describe('FinalizacionView', () => {
  it('6.1: uploading finalizacion report shows table of ungraded submissions', async () => {
    setupAuth()

    server.use(
      http.post(FINALIZACION_URL, () => HttpResponse.json(FINALIZACION_RESPONSE)),
    )

    renderWithProviders(<FinalizacionView asignacionId={ASIG_ID} />)

    const fileInput = screen.getByLabelText(/reporte de finalización/i)
    const file = new File(['csv'], 'finalizacion.csv', { type: 'text/csv' })
    await userEvent.upload(fileInput, file)

    await waitFor(() => {
      expect(screen.getByText('alumno@test.com')).toBeInTheDocument()
      expect(screen.getByText('Tarea Final')).toBeInTheDocument()
    })
  })

  it('6.3: export button generates CSV download from received data', async () => {
    setupAuth()

    server.use(
      http.post(FINALIZACION_URL, () => HttpResponse.json(FINALIZACION_RESPONSE)),
    )

    // Mock URL.createObjectURL and document.createElement anchor click
    const createObjectURL = vi.fn(() => 'blob:test-url')
    const revokeObjectURL = vi.fn()
    globalThis.URL.createObjectURL = createObjectURL
    globalThis.URL.revokeObjectURL = revokeObjectURL

    const clickSpy = vi.fn()
    const originalCreate = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = originalCreate(tag)
      if (tag === 'a') {
        vi.spyOn(el, 'click').mockImplementation(clickSpy)
      }
      return el
    })

    renderWithProviders(<FinalizacionView asignacionId={ASIG_ID} />)

    const fileInput = screen.getByLabelText(/reporte de finalización/i)
    const file = new File(['csv'], 'finalizacion.csv', { type: 'text/csv' })
    await userEvent.upload(fileInput, file)

    await waitFor(() => {
      expect(screen.getByText('alumno@test.com')).toBeInTheDocument()
    })

    const exportBtn = screen.getByRole('button', { name: /exportar csv/i })
    await userEvent.click(exportBtn)

    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob))
    expect(clickSpy).toHaveBeenCalled()

    vi.restoreAllMocks()
  })
})
