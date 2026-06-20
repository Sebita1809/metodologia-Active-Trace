/**
 * __tests__/CerrarLiquidacionDialog.test.tsx — Task 12.2
 *
 * Tests for CerrarLiquidacionDialog:
 *   - does not close without checkbox confirmation
 *   - liquidacion ya cerrada disables the button
 *   - confirming dispatches onConfirm
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/renderWithProviders'
import { CerrarLiquidacionDialog } from '../components/CerrarLiquidacionDialog'
import type { LiquidacionFilters, LiquidacionSegmentada } from '../types'

const FILTERS: LiquidacionFilters = { cohorte_id: 'coh-1', mes: 3, anio: 2025 }

const makeLiquidacion = (estado: string) => ({
  id: 'liq-1',
  tenant_id: 'tenant-1',
  usuario_id: 'user-1',
  cohorte_id: 'coh-1',
  periodo_mes: 3,
  periodo_anio: 2025,
  rol: 'PROFESOR',
  comisiones: [],
  base_monto: '50000.00',
  plus_monto: '5000.00',
  total_monto: '55000.00',
  desglose: null,
  es_nexo: false,
  excluido_por_factura: false,
  estado,
  cerrada_at: estado === 'Cerrada' ? '2025-03-31T00:00:00Z' : null,
  created_at: '2025-03-01T00:00:00Z',
  updated_at: '2025-03-01T00:00:00Z',
  deleted_at: null,
})

const makePeriodoData = (estado = 'Activa'): LiquidacionSegmentada => ({
  cohorte_id: 'coh-1',
  mes: 3,
  anio: 2025,
  general: { liquidaciones: [makeLiquidacion(estado)], total: '55000.00' },
  nexo: { liquidaciones: [], total: '0.00' },
  facturantes: { liquidaciones: [], total: '0.00' },
  total_sin_factura: '55000.00',
  total_con_factura: '55000.00',
})

describe('CerrarLiquidacionDialog', () => {
  it('12.2a: cerrar button is disabled without checkbox confirmation', () => {
    const onConfirm = vi.fn()
    renderWithProviders(
      <CerrarLiquidacionDialog
        filters={FILTERS}
        periodoData={makePeriodoData()}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
        isPending={false}
      />,
    )

    const cerrarBtn = screen.getByRole('button', { name: /cerrar liquidación/i })
    expect(cerrarBtn).toBeDisabled()
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('12.2b: liquidacion ya cerrada keeps button disabled even after checkbox', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <CerrarLiquidacionDialog
        filters={FILTERS}
        periodoData={makePeriodoData('Cerrada')}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        isPending={false}
      />,
    )

    // Check the confirmation checkbox
    const checkbox = screen.getByRole('checkbox')
    await user.click(checkbox)

    // Button still disabled because period is already closed
    const cerrarBtn = screen.getByRole('button', { name: /cerrar liquidación/i })
    expect(cerrarBtn).toBeDisabled()
  })

  it('12.2c: confirmar after checkbox dispatches onConfirm', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()

    renderWithProviders(
      <CerrarLiquidacionDialog
        filters={FILTERS}
        periodoData={makePeriodoData('Activa')}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
        isPending={false}
      />,
    )

    const checkbox = screen.getByRole('checkbox')
    await user.click(checkbox)

    const cerrarBtn = screen.getByRole('button', { name: /cerrar liquidación/i })
    expect(cerrarBtn).not.toBeDisabled()

    await user.click(cerrarBtn)
    expect(onConfirm).toHaveBeenCalledOnce()
  })
})
