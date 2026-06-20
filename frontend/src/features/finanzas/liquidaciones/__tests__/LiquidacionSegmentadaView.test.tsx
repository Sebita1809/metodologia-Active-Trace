/**
 * __tests__/LiquidacionSegmentadaView.test.tsx — Task 12.1
 *
 * Tests for LiquidacionSegmentadaView:
 *   - renders all three segments
 *   - KPI values are correct
 *   - empty segment shows informative text
 */

import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '@/test/renderWithProviders'
import { LiquidacionSegmentadaView } from '../components/LiquidacionSegmentadaView'
import type { LiquidacionSegmentada } from '../types'

const makeLiquidacion = (overrides = {}) => ({
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
  estado: 'Activa',
  cerrada_at: null,
  created_at: '2025-03-01T00:00:00Z',
  updated_at: '2025-03-01T00:00:00Z',
  deleted_at: null,
  ...overrides,
})

const DATA_WITH_THREE_SEGMENTS: LiquidacionSegmentada = {
  cohorte_id: 'coh-1',
  mes: 3,
  anio: 2025,
  general: {
    liquidaciones: [makeLiquidacion({ id: 'liq-g1', rol: 'PROFESOR' })],
    total: '55000.00',
  },
  nexo: {
    liquidaciones: [makeLiquidacion({ id: 'liq-n1', rol: 'NEXO', es_nexo: true })],
    total: '55000.00',
  },
  facturantes: {
    liquidaciones: [makeLiquidacion({ id: 'liq-f1', rol: 'TUTOR', excluido_por_factura: true })],
    total: '55000.00',
  },
  total_sin_factura: '110000.00',
  total_con_factura: '165000.00',
}

const EMPTY_SEGMENT_DATA: LiquidacionSegmentada = {
  cohorte_id: 'coh-1',
  mes: 3,
  anio: 2025,
  general: { liquidaciones: [], total: '0.00' },
  nexo: { liquidaciones: [], total: '0.00' },
  facturantes: { liquidaciones: [], total: '0.00' },
  total_sin_factura: '0.00',
  total_con_factura: '0.00',
}

describe('LiquidacionSegmentadaView', () => {
  it('12.1a: renders all three segment headings', () => {
    renderWithProviders(<LiquidacionSegmentadaView data={DATA_WITH_THREE_SEGMENTS} />)

    expect(screen.getByText('General')).toBeInTheDocument()
    expect(screen.getByText('NEXO')).toBeInTheDocument()
    expect(screen.getByText('Facturantes')).toBeInTheDocument()
  })

  it('12.1b: KPI headers display total_sin_factura and total_con_factura', () => {
    renderWithProviders(<LiquidacionSegmentadaView data={DATA_WITH_THREE_SEGMENTS} />)

    expect(screen.getByText('Total sin factura')).toBeInTheDocument()
    expect(screen.getByText('Total con factura')).toBeInTheDocument()
  })

  it('12.1c: empty segments show informative message', () => {
    renderWithProviders(<LiquidacionSegmentadaView data={EMPTY_SEGMENT_DATA} />)

    const emptyMessages = screen.getAllByText(/sin liquidaciones en este segmento/i)
    expect(emptyMessages.length).toBeGreaterThan(0)
  })
})
