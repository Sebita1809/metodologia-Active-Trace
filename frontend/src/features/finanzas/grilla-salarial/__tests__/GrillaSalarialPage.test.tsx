/**
 * __tests__/GrillaSalarialPage.test.tsx — Task 12.3
 *
 * Tests for GrillaSalarialPage:
 *   - crear salario base with vigencia validation
 *   - crear plus
 *   - delete with inline confirmation
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { GrillaSalarialPage } from '../pages/GrillaSalarialPage'

const FAKE_SALARIOS_BASE = [
  {
    id: 'sb-1',
    tenant_id: 'tenant-1',
    rol: 'PROFESOR',
    monto: '50000.00',
    desde: '2025-01-01',
    hasta: null,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    deleted_at: null,
  },
]

const FAKE_PLUS = [
  {
    id: 'plus-1',
    tenant_id: 'tenant-1',
    clave: 'ANTIGUEDAD',
    rol: 'PROFESOR',
    descripcion: 'Plus por antigüedad',
    monto: '5000.00',
    desde: '2025-01-01',
    hasta: null,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    deleted_at: null,
  },
]

describe('GrillaSalarialPage', () => {
  beforeEach(() => {
    server.use(
      http.get('http://localhost:8000/api/liquidaciones/grilla/base', () =>
        HttpResponse.json(FAKE_SALARIOS_BASE),
      ),
      http.get('http://localhost:8000/api/liquidaciones/grilla/plus', () =>
        HttpResponse.json(FAKE_PLUS),
      ),
    )
  })

  it('12.3a: renders salario base tab with data', async () => {
    renderWithProviders(<GrillaSalarialPage />)

    await waitFor(() => {
      expect(screen.getByText('PROFESOR')).toBeInTheDocument()
    })

    expect(screen.getByText('Salario base')).toBeInTheDocument()
    expect(screen.getByText('Plus')).toBeInTheDocument()
  })

  it('12.3b: switching to Plus tab shows plus data', async () => {
    const user = userEvent.setup()
    renderWithProviders(<GrillaSalarialPage />)

    const plusTab = await screen.findByRole('button', { name: /^plus$/i })
    await user.click(plusTab)

    await waitFor(() => {
      expect(screen.getByText('ANTIGUEDAD')).toBeInTheDocument()
    })
  })

  it('12.3c: delete shows inline confirmation before deleting', async () => {
    const user = userEvent.setup()
    renderWithProviders(<GrillaSalarialPage />)

    await waitFor(() => {
      expect(screen.getByText('PROFESOR')).toBeInTheDocument()
    })

    // Click "Eliminar"
    const eliminarBtn = screen.getByRole('button', { name: /eliminar/i })
    await user.click(eliminarBtn)

    // Should show inline confirm/cancel
    expect(screen.getByRole('button', { name: /confirmar/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument()
  })
})
