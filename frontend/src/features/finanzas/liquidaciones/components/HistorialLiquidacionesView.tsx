/**
 * HistorialLiquidacionesView.tsx — Table of closed liquidation periods.
 *
 * Shows: período (mes/anio), cohorte, rol, total, fecha de cierre.
 * Read-only — no actions. Closed periods cannot be modified.
 */

import { useHistorialLiquidaciones } from '../hooks/useLiquidaciones'

const MESES_LABEL = [
  '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

function formatARS(value: string): string {
  return parseFloat(value).toLocaleString('es-AR', {
    style: 'currency',
    currency: 'ARS',
  })
}

function formatDate(isoString: string | null): string {
  if (!isoString) return '—'
  return new Date(isoString).toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function HistorialLiquidacionesView() {
  const { data, isLoading, error } = useHistorialLiquidaciones()

  if (isLoading) {
    return <p className="text-sm text-gray-500 py-4">Cargando historial...</p>
  }

  if (error) {
    return (
      <p className="text-sm text-red-600 py-4">
        Error al cargar el historial. Intentá de nuevo.
      </p>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-sm">No hay liquidaciones cerradas aún.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-medium text-gray-700">
        Períodos cerrados ({data.length})
      </h2>
      <div className="overflow-x-auto rounded-md border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Período
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cohorte
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rol
              </th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Total
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Fecha de cierre
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {data.map((liq) => (
              <tr key={liq.id}>
                <td className="px-4 py-2 text-gray-700">
                  {MESES_LABEL[liq.periodo_mes]} {liq.periodo_anio}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-gray-500">
                  {liq.cohorte_id.slice(0, 8)}…
                </td>
                <td className="px-4 py-2 text-gray-700">{liq.rol}</td>
                <td className="px-4 py-2 text-right font-medium text-gray-900">
                  {formatARS(liq.total_monto)}
                </td>
                <td className="px-4 py-2 text-gray-600">
                  {formatDate(liq.cerrada_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
