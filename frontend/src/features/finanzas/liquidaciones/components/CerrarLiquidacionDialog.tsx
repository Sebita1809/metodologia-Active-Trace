/**
 * CerrarLiquidacionDialog.tsx — Double-confirmation dialog for closing a liquidacion period.
 *
 * RN-22: Closing is irreversible. Must show period and total before executing.
 */

import { useState } from 'react'
import type { LiquidacionFilters, LiquidacionSegmentada } from '../types'

interface CerrarLiquidacionDialogProps {
  filters: LiquidacionFilters
  periodoData: LiquidacionSegmentada
  onConfirm: () => void
  onCancel: () => void
  isPending: boolean
}

const MESES_LABEL = [
  '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

export function CerrarLiquidacionDialog({
  filters,
  periodoData,
  onConfirm,
  onCancel,
  isPending,
}: CerrarLiquidacionDialogProps) {
  const [confirmed, setConfirmed] = useState(false)

  const periodoLabel = `${MESES_LABEL[filters.mes]} ${filters.anio}`
  const totalSinFactura = parseFloat(periodoData.total_sin_factura).toLocaleString('es-AR', {
    style: 'currency',
    currency: 'ARS',
  })

  // Check if any liquidacion is already closed
  const allLiquidaciones = [
    ...periodoData.general.liquidaciones,
    ...periodoData.nexo.liquidaciones,
    ...periodoData.facturantes.liquidaciones,
  ]
  const yaEstaCerrada = allLiquidaciones.some((l) => l.estado === 'Cerrada')

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          ¿Cerrar liquidación?
        </h2>
        <p className="text-sm text-red-600 font-medium mb-4">
          Esta acción es <strong>irreversible</strong>. Una vez cerrada, la liquidación no puede modificarse.
        </p>

        <div className="bg-gray-50 rounded-md p-4 mb-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Período:</span>
            <span className="font-medium text-gray-900">{periodoLabel}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Total sin factura:</span>
            <span className="font-medium text-gray-900">{totalSinFactura}</span>
          </div>
        </div>

        {yaEstaCerrada && (
          <div className="bg-amber-50 border border-amber-200 rounded-md p-3 mb-4">
            <p className="text-sm text-amber-700">
              Este período ya contiene liquidaciones cerradas.
            </p>
          </div>
        )}

        <label className="flex items-start gap-2 mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            className="mt-0.5"
          />
          <span className="text-sm text-gray-700">
            Confirmo que quiero cerrar la liquidación del período{' '}
            <strong>{periodoLabel}</strong> por un total de{' '}
            <strong>{totalSinFactura}</strong>. Entiendo que esta acción no tiene rollback.
          </span>
        </label>

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={isPending}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={!confirmed || isPending || yaEstaCerrada}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPending ? 'Cerrando...' : 'Cerrar liquidación'}
          </button>
        </div>
      </div>
    </div>
  )
}
