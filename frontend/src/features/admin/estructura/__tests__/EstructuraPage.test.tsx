/**
 * __tests__/EstructuraPage.test.tsx — Task 12.4
 *
 * Tests for EstructuraPage:
 *   - crear carrera shows form
 *   - toggle estado cohorte dispatches patch
 *   - validación de fechas cohorte
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { EstructuraPage } from '../pages/EstructuraPage'

const FAKE_CARRERAS = [
  {
    id: 'car-1',
    tenant_id: 'tenant-1',
    codigo: 'ING-SIS',
    nombre: 'Ingeniería en Sistemas',
    estado: 'Activa',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    deleted_at: null,
  },
]

const FAKE_COHORTES = [
  {
    id: 'coh-1',
    tenant_id: 'tenant-1',
    carrera_id: 'car-1',
    nombre: 'Cohorte 2024',
    anio: 2024,
    vig_desde: '2024-01-01',
    vig_hasta: null,
    estado: 'Activa',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    deleted_at: null,
  },
]

const FAKE_MATERIAS: unknown[] = []

describe('EstructuraPage', () => {
  beforeEach(() => {
    server.use(
      http.get('http://localhost:8000/api/admin/carreras', () =>
        HttpResponse.json(FAKE_CARRERAS),
      ),
      http.get('http://localhost:8000/api/admin/cohortes', () =>
        HttpResponse.json(FAKE_COHORTES),
      ),
      http.get('http://localhost:8000/api/admin/materias', () =>
        HttpResponse.json(FAKE_MATERIAS),
      ),
    )
  })

  it('12.4a: renders tabs for Carreras, Cohortes, Materias', async () => {
    renderWithProviders(<EstructuraPage />)

    expect(screen.getByRole('button', { name: 'Carreras' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cohortes' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Materias' })).toBeInTheDocument()
  })

  it('12.4b: carrera data is displayed in the table', async () => {
    renderWithProviders(<EstructuraPage />)

    await waitFor(() => {
      expect(screen.getByText('ING-SIS')).toBeInTheDocument()
    })
    expect(screen.getByText('Ingeniería en Sistemas')).toBeInTheDocument()
  })

  it('12.4c: "Nueva carrera" button opens create form', async () => {
    const user = userEvent.setup()
    renderWithProviders(<EstructuraPage />)

    await waitFor(() => {
      expect(screen.getByText('ING-SIS')).toBeInTheDocument()
    })

    const newCarreraBtn = screen.getByRole('button', { name: /\+ nueva carrera/i })
    await user.click(newCarreraBtn)

    expect(screen.getByText('Nueva carrera')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/ej: ing-sis/i)).toBeInTheDocument()
  })

  it('12.4d: cohorte toggle calls PATCH endpoint', async () => {
    const user = userEvent.setup()
    const patchCalled = vi.fn()

    server.use(
      http.patch('http://localhost:8000/api/admin/cohortes/coh-1', async ({ request }) => {
        const body = await request.json()
        patchCalled(body)
        return HttpResponse.json({ ...FAKE_COHORTES[0], estado: 'Inactiva' })
      }),
    )

    renderWithProviders(<EstructuraPage />)

    // Switch to Cohortes tab
    const cohorteTab = screen.getByRole('button', { name: 'Cohortes' })
    await user.click(cohorteTab)

    await waitFor(() => {
      expect(screen.getByText('Cohorte 2024')).toBeInTheDocument()
    })

    const desactivarBtn = screen.getByRole('button', { name: /desactivar/i })
    await user.click(desactivarBtn)

    await waitFor(() => {
      expect(patchCalled).toHaveBeenCalledWith(expect.objectContaining({ estado: 'Inactiva' }))
    })
  })
})
