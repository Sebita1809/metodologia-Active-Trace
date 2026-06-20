/**
 * __tests__/AsignacionesView.test.tsx
 *
 * Tests for task 13.1 — AsignacionesView:
 *   - render with data
 *   - filter by rol
 *   - export button dispatches download
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { AsignacionesView } from '../equipos/components/AsignacionesView'

const ASIG_URL = 'http://localhost:8000/api/asignaciones'
const EXPORT_URL = 'http://localhost:8000/api/equipos/asignaciones/exportar'

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['COORDINADOR'] })
  tokenStorage.setTokens(jwt, jwt)
}

const ASIGNACIONES = [
  {
    id: 'asig-1',
    tenant_id: 'tenant-abc',
    usuario_id: 'user-prof-1',
    rol: 'TUTOR',
    materia_id: 'mat-1',
    carrera_id: null,
    cohorte_id: null,
    comisiones: [],
    responsable_id: null,
    desde: '2025-01-01',
    hasta: null,
    estado_vigencia: 'Vigente',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'asig-2',
    tenant_id: 'tenant-abc',
    usuario_id: 'user-prof-2',
    rol: 'PROFESOR',
    materia_id: 'mat-2',
    carrera_id: null,
    cohorte_id: null,
    comisiones: [],
    responsable_id: null,
    desde: '2025-01-01',
    hasta: '2025-12-31',
    estado_vigencia: 'Vigente',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
]

describe('AsignacionesView', () => {
  it('13.1a: renders table with asignaciones data', async () => {
    setupAuth()
    server.use(
      http.get(ASIG_URL, () => HttpResponse.json(ASIGNACIONES)),
    )

    renderWithProviders(<AsignacionesView />)

    await waitFor(() => {
      expect(screen.getByText('user-prof-1')).toBeInTheDocument()
      expect(screen.getByText('user-prof-2')).toBeInTheDocument()
    })
  })

  it('13.1b: filter by rol sends request with rol param', async () => {
    setupAuth()
    let capturedUrl = ''

    server.use(
      http.get(ASIG_URL, ({ request }) => {
        capturedUrl = request.url
        return HttpResponse.json([ASIGNACIONES[0]])
      }),
    )

    renderWithProviders(<AsignacionesView />)

    await waitFor(() => {
      expect(screen.getByText('user-prof-1')).toBeInTheDocument()
    })

    // Select TUTOR role
    const rolSelect = screen.getByRole('combobox')
    await userEvent.selectOptions(rolSelect, 'TUTOR')

    await waitFor(() => {
      expect(capturedUrl).toContain('rol=TUTOR')
    })
  })

  it('13.1c: export button triggers download when clicked', async () => {
    setupAuth()
    let exportCalled = false

    server.use(
      http.get(ASIG_URL, () => HttpResponse.json([])),
      http.get(EXPORT_URL, () => {
        exportCalled = true
        return new HttpResponse('col1,col2\nval1,val2', {
          headers: { 'Content-Type': 'text/csv' },
        })
      }),
    )

    // Mock URL.createObjectURL
    const createObjectURL = vi.fn(() => 'blob:fake-url')
    const revokeObjectURL = vi.fn()
    global.URL.createObjectURL = createObjectURL
    global.URL.revokeObjectURL = revokeObjectURL

    renderWithProviders(<AsignacionesView />)

    const exportBtn = await screen.findByRole('button', { name: /exportar csv/i })
    await userEvent.click(exportBtn)

    await waitFor(() => {
      expect(exportCalled).toBe(true)
    })
  })
})
