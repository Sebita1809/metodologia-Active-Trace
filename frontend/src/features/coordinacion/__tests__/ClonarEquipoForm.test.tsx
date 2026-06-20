/**
 * __tests__/ClonarEquipoForm.test.tsx
 *
 * Tests for task 13.2 — ClonarEquipoForm:
 *   - validates required origin and destination fields
 *   - warns when destination has existing asignaciones
 *   - successful clone submission
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { ClonarEquipoForm } from '../equipos/components/ClonarEquipoForm'

const ASIG_URL = 'http://localhost:8000/api/asignaciones'
const CLONAR_URL = 'http://localhost:8000/api/equipos/asignaciones/clonar'

const VALID_UUID = '00000000-0000-0000-0000-000000000001'
const VALID_UUID2 = '00000000-0000-0000-0000-000000000002'
const VALID_UUID3 = '00000000-0000-0000-0000-000000000003'
const VALID_UUID4 = '00000000-0000-0000-0000-000000000004'
const VALID_UUID5 = '00000000-0000-0000-0000-000000000005'
const VALID_UUID6 = '00000000-0000-0000-0000-000000000006'

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['COORDINADOR'] })
  tokenStorage.setTokens(jwt, jwt)
}

describe('ClonarEquipoForm', () => {
  it('13.2a: shows validation error when origen fields are empty', async () => {
    setupAuth()
    server.use(http.get(ASIG_URL, () => HttpResponse.json([])))

    renderWithProviders(<ClonarEquipoForm />)

    const submitBtn = screen.getByRole('button', { name: /clonar equipo/i })
    await userEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/seleccioná la materia de origen/i)).toBeInTheDocument()
    })
  })

  it('13.2b: shows warning when destination has existing asignaciones', async () => {
    setupAuth()
    server.use(
      http.get(ASIG_URL, ({ request }) => {
        const url = new URL(request.url)
        const materiaId = url.searchParams.get('materia_id')
        // Return existing asignaciones when querying destination materia
        if (materiaId === VALID_UUID4) {
          return HttpResponse.json([{ id: 'existing-asig', rol: 'TUTOR' }])
        }
        return HttpResponse.json([])
      }),
    )

    renderWithProviders(<ClonarEquipoForm />)

    const inputs = screen.getAllByPlaceholderText(/uuid/i)
    // Fill origen fields
    await userEvent.type(inputs[0], VALID_UUID)
    await userEvent.type(inputs[1], VALID_UUID2)
    await userEvent.type(inputs[2], VALID_UUID3)
    // Fill destino fields (materia_id = VALID_UUID4 triggers warning)
    await userEvent.type(inputs[3], VALID_UUID4)
    await userEvent.type(inputs[4], VALID_UUID5)
    await userEvent.type(inputs[5], VALID_UUID6)

    await waitFor(() => {
      expect(screen.getByText(/destino ya tiene/i)).toBeInTheDocument()
    })
  })

  it('13.2c: successful clone calls API and invokes onSuccess', async () => {
    setupAuth()
    let clonarCalled = false

    server.use(
      http.get(ASIG_URL, () => HttpResponse.json([])),
      http.post(CLONAR_URL, async () => {
        clonarCalled = true
        return HttpResponse.json({ asignaciones_creadas: 5, advertencia: null })
      }),
    )

    const onSuccess = vi.fn()
    renderWithProviders(<ClonarEquipoForm onSuccess={onSuccess} />)

    const inputs = screen.getAllByPlaceholderText(/uuid/i)
    await userEvent.type(inputs[0], VALID_UUID)
    await userEvent.type(inputs[1], VALID_UUID2)
    await userEvent.type(inputs[2], VALID_UUID3)
    await userEvent.type(inputs[3], VALID_UUID4)
    await userEvent.type(inputs[4], VALID_UUID5)
    await userEvent.type(inputs[5], VALID_UUID6)

    const submitBtn = screen.getByRole('button', { name: /clonar equipo/i })
    await userEvent.click(submitBtn)

    await waitFor(() => {
      expect(clonarCalled).toBe(true)
      expect(onSuccess).toHaveBeenCalled()
    })
  })
})
