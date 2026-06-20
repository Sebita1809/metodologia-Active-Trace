/**
 * __tests__/UsuarioAdminForm.test.tsx — Task 12.5
 *
 * Tests for UsuarioAdminForm:
 *   - validation of required fields
 *   - CBU validation (22 digits)
 *   - CBU never in URL params (spy on axios)
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/test/renderWithProviders'
import { server } from '@/test/mswServer'
import { UsuarioAdminForm } from '../components/UsuarioAdminForm'

describe('UsuarioAdminForm', () => {
  it('12.5a: required fields — submitting empty form shows errors', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    renderWithProviders(
      <UsuarioAdminForm onSubmit={onSubmit} onCancel={vi.fn()} isPending={false} />,
    )

    const submitBtn = screen.getByRole('button', { name: /crear usuario/i })
    await user.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/el nombre es requerido/i)).toBeInTheDocument()
    })

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('12.5b: CBU validation — 21 digits is invalid', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    renderWithProviders(
      <UsuarioAdminForm onSubmit={onSubmit} onCancel={vi.fn()} isPending={false} />,
    )

    // Fill required fields first
    await user.type(screen.getByLabelText(/^nombre/i), 'Juan')
    await user.type(screen.getByLabelText(/^apellidos/i), 'García')
    await user.type(screen.getByLabelText(/^email/i), 'juan@example.com')

    // Set invalid CBU (21 digits)
    const cbuInput = screen.getByPlaceholderText(/22 dígitos/i)
    await user.type(cbuInput, '123456789012345678901')

    const submitBtn = screen.getByRole('button', { name: /crear usuario/i })
    await user.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/cbu debe tener 22 dígitos/i)).toBeInTheDocument()
    })

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('12.5c: POST request does NOT contain CBU in URL (never in query params)', async () => {
    const user = userEvent.setup()
    let capturedUrl = ''

    server.use(
      http.post('http://localhost:8000/api/admin/usuarios', ({ request }) => {
        capturedUrl = request.url
        return HttpResponse.json({
          id: 'new-user',
          tenant_id: 'tenant-1',
          nombre: 'Ana',
          apellidos: 'López',
          email: 'ana@example.com',
          dni: null, cuil: null, cbu: '1234567890123456789012',
          alias_cbu: null, banco: null, regional: null, legajo: null,
          legajo_profesional: null, sexo: null, modalidad_cobro: null,
          facturador: false, estado: 'Activo',
          created_at: '2025-01-01T00:00:00Z', updated_at: '2025-01-01T00:00:00Z',
        })
      }),
    )

    const onSubmit = vi.fn()
    renderWithProviders(
      <UsuarioAdminForm onSubmit={onSubmit} onCancel={vi.fn()} isPending={false} />,
    )

    await user.type(screen.getByLabelText(/^nombre/i), 'Ana')
    await user.type(screen.getByLabelText(/^apellidos/i), 'López')
    await user.type(screen.getByLabelText(/^email/i), 'ana@example.com')
    await user.type(screen.getByPlaceholderText(/22 dígitos/i), '1234567890123456789012')

    const submitBtn = screen.getByRole('button', { name: /crear usuario/i })
    await user.click(submitBtn)

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled()
    })

    // CBU must NOT appear in the URL
    expect(capturedUrl).not.toContain('cbu')
    expect(capturedUrl).not.toContain('1234567890123456789012')
  })

  it('7.3: submit with empty CBU sends null', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    renderWithProviders(
      <UsuarioAdminForm
        initial={{
          id: 'usr-1',
          tenant_id: 't-1',
          nombre: 'Pepe',
          apellidos: 'Gómez',
          email: 'pepe@example.com',
          dni: null,
          cuil: null,
          cbu: null,
          alias_cbu: null,
          banco: null,
          regional: null,
          legajo: null,
          legajo_profesional: null,
          sexo: null,
          modalidad_cobro: null,
          facturador: false,
          estado: 'Activo',
          roles: [],
          created_at: '2025-06-01T00:00:00Z',
          updated_at: '2025-06-01T00:00:00Z',
        }}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
        isPending={false}
      />,
    )

    const submitBtn = screen.getByRole('button', { name: /guardar cambios/i })
    await user.click(submitBtn)

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled()
    })

    const submittedData = onSubmit.mock.calls[0][0]
    expect(submittedData.cbu).toBeNull()
  })
})
