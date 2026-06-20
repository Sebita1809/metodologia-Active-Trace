/**
 * __tests__/AvisoForm.test.tsx
 *
 * Tests for task 13.3 — AvisoForm:
 *   - conditional context validation (materia required when alcance=materia)
 *   - fecha_fin > fecha_inicio validation
 *   - require_ack toggle works
 */

import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/renderWithProviders'
import { makeFakeJwt } from '@/test/fixtures'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { AvisoForm } from '../avisos/components/AvisoForm'

function setupAuth() {
  const jwt = makeFakeJwt({ roles: ['COORDINADOR'] })
  tokenStorage.setTokens(jwt, jwt)
}

describe('AvisoForm', () => {
  it('13.3a: shows materia error when alcance is "materia" but no materia selected', async () => {
    setupAuth()
    renderWithProviders(<AvisoForm />)

    // Fill titulo and cuerpo
    await userEvent.type(screen.getByRole('textbox', { name: /título/i }), 'Test aviso')
    await userEvent.type(screen.getByRole('textbox', { name: /cuerpo/i }), 'Test body')

    // Change alcance to materia
    const alcanceSelect = screen.getByRole('combobox', { name: /alcance/i })
    await userEvent.selectOptions(alcanceSelect, 'materia')

    // Fill fecha_inicio
    const fechaInicioInput = screen.getByLabelText(/fecha inicio/i)
    await userEvent.type(fechaInicioInput, '2025-01-01')

    // Select a rol
    const tutorCheckbox = screen.getByRole('checkbox', { name: /tutor/i })
    await userEvent.click(tutorCheckbox)

    // Submit without filling materia
    const submitBtn = screen.getByRole('button', { name: /crear aviso/i })
    await userEvent.click(submitBtn)

    await waitFor(() => {
      expect(
        screen.getByText(/materia es obligatoria cuando el alcance es "materia"/i),
      ).toBeInTheDocument()
    })
  })

  it('13.3b: shows fecha_fin error when fecha_fin is before fecha_inicio', async () => {
    setupAuth()
    renderWithProviders(<AvisoForm />)

    await userEvent.type(screen.getByRole('textbox', { name: /título/i }), 'Test aviso')
    await userEvent.type(screen.getByRole('textbox', { name: /cuerpo/i }), 'Test body')

    const tutorCheckbox = screen.getByRole('checkbox', { name: /tutor/i })
    await userEvent.click(tutorCheckbox)

    const fechaInicioInput = screen.getByLabelText(/fecha inicio/i)
    await userEvent.type(fechaInicioInput, '2025-06-01')

    const fechaFinInput = screen.getByLabelText(/fecha fin/i)
    await userEvent.type(fechaFinInput, '2025-05-01')

    const submitBtn = screen.getByRole('button', { name: /crear aviso/i })
    await userEvent.click(submitBtn)

    await waitFor(() => {
      expect(
        screen.getByText(/la fecha de fin debe ser posterior a la fecha de inicio/i),
      ).toBeInTheDocument()
    })
  })

  it('13.3c: require_ack checkbox toggles correctly', async () => {
    setupAuth()
    renderWithProviders(<AvisoForm />)

    const requireAckCheckbox = screen.getByRole('checkbox', {
      name: /requiere confirmación de lectura/i,
    })

    expect(requireAckCheckbox).not.toBeChecked()
    await userEvent.click(requireAckCheckbox)
    expect(requireAckCheckbox).toBeChecked()
    await userEvent.click(requireAckCheckbox)
    expect(requireAckCheckbox).not.toBeChecked()
  })
})
