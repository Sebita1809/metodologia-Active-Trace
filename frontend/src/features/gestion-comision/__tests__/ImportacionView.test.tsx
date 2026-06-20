/**
 * __tests__/ImportacionView.test.tsx
 *
 * Tests for tasks 5.1, 5.3, 5.4, 5.6 — Importación de calificaciones.
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { ImportacionView } from '../components/import/ImportacionView'

const ASIG_ID = 'asig-test-1'
const PREVIEW_URL = 'http://localhost:8000/api/calificaciones/preview'
const IMPORT_URL = 'http://localhost:8000/api/calificaciones/import'

const PREVIEW_RESPONSE = {
  actividades_numericas: ['Tarea 1', 'Tarea 2'],
  actividades_textuales: ['Presentación'],
  alumnos_detectados: 15,
}

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['PROFESOR'], sub: 'user-123' })
  tokenStorage.setTokens(jwt, jwt)
}

function makeFile(name = 'grades.csv') {
  return new File(['csv content'], name, { type: 'text/csv' })
}

describe('ImportacionView', () => {
  it('5.1: uploading file calls preview and shows detected activities without persisting', async () => {
    setupAuth()

    const previewCalled = { count: 0 }
    server.use(
      http.post(PREVIEW_URL, async () => {
        previewCalled.count++
        return HttpResponse.json(PREVIEW_RESPONSE)
      }),
    )

    renderWithProviders(<ImportacionView asignacionId={ASIG_ID} />)

    const fileInput = screen.getByLabelText(/archivo de calificaciones/i)
    await userEvent.upload(fileInput, makeFile())

    // Should show detected activities
    await waitFor(() => {
      expect(screen.getByText(/Tarea 1/)).toBeInTheDocument()
      expect(screen.getByText(/Tarea 2/)).toBeInTheDocument()
    })

    // Preview was called, not import
    expect(previewCalled.count).toBe(1)
  })

  it('5.3: 422 error in preview shows error message and allows retry', async () => {
    setupAuth()

    server.use(
      http.post(PREVIEW_URL, () =>
        HttpResponse.json(
          { detail: 'Formato de archivo inválido' },
          { status: 422 },
        ),
      ),
    )

    renderWithProviders(<ImportacionView asignacionId={ASIG_ID} />)

    const fileInput = screen.getByLabelText(/archivo de calificaciones/i)
    await userEvent.upload(fileInput, makeFile('bad.txt'))

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument()
    })

    // The file input should still be present to allow retry
    expect(screen.getByLabelText(/archivo de calificaciones/i)).toBeInTheDocument()
  })

  it('5.4: selecting activities and confirming sends multipart shape and reflects 201', async () => {
    setupAuth()

    let capturedFormData: FormData | null = null
    server.use(
      http.post(PREVIEW_URL, () => HttpResponse.json(PREVIEW_RESPONSE)),
      http.post(IMPORT_URL, async ({ request }) => {
        capturedFormData = await request.formData()
        return HttpResponse.json([], { status: 201 })
      }),
    )

    renderWithProviders(<ImportacionView asignacionId={ASIG_ID} />)

    // Upload file to trigger preview
    const fileInput = screen.getByLabelText(/archivo de calificaciones/i)
    await userEvent.upload(fileInput, makeFile())

    // Wait for activities to appear and select one
    const checkbox = await screen.findByRole('checkbox', { name: /Tarea 1/i })
    await userEvent.click(checkbox)

    // Confirm import
    const confirmBtn = screen.getByRole('button', { name: /confirmar importación/i })
    await userEvent.click(confirmBtn)

    await waitFor(() => {
      expect(capturedFormData).not.toBeNull()
      // Should have file and request JSON fields
      expect(capturedFormData!.has('file')).toBe(true)
      expect(capturedFormData!.has('request')).toBe(true)
    })

    // Should show success feedback
    await waitFor(() => {
      expect(screen.getByText(/importad/i)).toBeInTheDocument()
    })
  })

  it('5.6: confirm button is disabled when no activities are selected', async () => {
    setupAuth()

    server.use(
      http.post(PREVIEW_URL, () => HttpResponse.json(PREVIEW_RESPONSE)),
    )

    renderWithProviders(<ImportacionView asignacionId={ASIG_ID} />)

    const fileInput = screen.getByLabelText(/archivo de calificaciones/i)
    await userEvent.upload(fileInput, makeFile())

    await waitFor(() => {
      expect(screen.getByText(/Tarea 1/)).toBeInTheDocument()
    })

    // No checkboxes selected → confirm should be disabled
    const confirmBtn = screen.getByRole('button', { name: /confirmar importación/i })
    expect(confirmBtn).toBeDisabled()
  })
})
