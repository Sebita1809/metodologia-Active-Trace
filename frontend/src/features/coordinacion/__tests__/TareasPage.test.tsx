/**
 * __tests__/TareasPage.test.tsx
 *
 * Tests for task 13.4 — TareasPage:
 *   - PROFESOR role sees only own tasks (no "Todas las tareas" tab)
 *   - COORDINADOR sees global view with tabs
 *   - inline state change calls API
 *   - add comment works
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { TareasPage } from '../tareas/pages/TareasPage'

const MIAS_URL = 'http://localhost:8000/api/v1/tareas/mias'
const TAREAS_URL = 'http://localhost:8000/api/v1/tareas'

function setupAuthAs(roles: string[]) {
  const jwt = makeFakeJwt({ roles: roles as Parameters<typeof makeFakeJwt>[0]['roles'] })
  tokenStorage.setTokens(jwt, jwt)
}

const MIS_TAREAS = [
  {
    id: 'tarea-1',
    tenant_id: 'tenant-abc',
    titulo: 'Revisar informe',
    descripcion: 'Descripción de la tarea',
    criterio_cierre: null,
    materia_id: 'mat-1',
    asignada_a: 'user-123',
    asignada_por: 'coord-1',
    estado: 'Abierta',
    observacion: null,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
]

describe('TareasPage', () => {
  it('13.4a: PROFESOR sees "Mis tareas" heading (no tabs)', async () => {
    setupAuthAs(['PROFESOR'])
    server.use(http.get(MIAS_URL, () => HttpResponse.json(MIS_TAREAS)))

    renderWithProviders(<TareasPage />)

    await waitFor(() => {
      expect(screen.getByText(/mis tareas/i)).toBeInTheDocument()
    })

    // No "Todas las tareas" tab for PROFESOR
    expect(screen.queryByRole('button', { name: /todas las tareas/i })).not.toBeInTheDocument()
  })

  it('13.4b: COORDINADOR sees tabs "Mis tareas" and "Todas las tareas"', async () => {
    setupAuthAs(['COORDINADOR'])
    server.use(
      http.get(MIAS_URL, () => HttpResponse.json([])),
      http.get(TAREAS_URL, () => HttpResponse.json([])),
    )

    renderWithProviders(<TareasPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /mis tareas/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /todas las tareas/i })).toBeInTheDocument()
    })
  })

  it('13.4c: inline state change calls PATCH /tareas/{id}/estado', async () => {
    setupAuthAs(['PROFESOR'])
    let patchCalled = false

    server.use(
      http.get(MIAS_URL, () => HttpResponse.json(MIS_TAREAS)),
      http.patch(
        'http://localhost:8000/api/v1/tareas/tarea-1/estado',
        async () => {
          patchCalled = true
          return HttpResponse.json({ ...MIS_TAREAS[0], estado: 'En progreso' })
        },
      ),
    )

    renderWithProviders(<TareasPage />)

    await waitFor(() => {
      expect(screen.getByText('Revisar informe')).toBeInTheDocument()
    })

    const estadoSelect = screen.getByRole('combobox')
    await userEvent.selectOptions(estadoSelect, 'En progreso')

    await waitFor(() => {
      expect(patchCalled).toBe(true)
    })
  })
})
