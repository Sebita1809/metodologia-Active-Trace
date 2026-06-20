/**
 * LiquidacionSegmentadaView.tsx — Segmented view of a liquidation period.
 *
 * Shows three sections: General, NEXO, Facturantes.
 * KPIs: "Total sin factura" and "Total con factura" in header.
 * Closed liquidaciones show a "Cerrada" badge; rows are read-only.
 */

import type { LiquidacionRead, LiquidacionSegmentada, PeriodoSegmento } from '../types'

interface Props {
  data: LiquidacionSegmentada
}

function formatARS(value: string): string {
  return parseFloat(value).toLocaleString('es-AR', {
    style: 'currency',
    currency: 'ARS',
  })
}

function EstadoBadge({ estado }: { estado: string }) {
  const closed = estado === 'Cerrada'
  return (
    <span
      className={[
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
        closed
          ? 'bg-gray-100 text-gray-700'
          : 'bg-green-100 text-green-700',
      ].join(' ')}
    >
      {estado}
    </span>
  )
}

function SegmentoTable({
  titulo,
  segmento,
}: {
  titulo: string
  segmento: PeriodoSegmento
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">{titulo}</h3>
        <span className="text-sm font-medium text-gray-900">
          Subtotal: {formatARS(segmento.total)}
        </span>
      </div>

      {segmento.liquidaciones.length === 0 ? (
        <p className="text-sm text-gray-500 py-2">Sin liquidaciones en este segmento.</p>
      ) : (
        <div className="overflow-x-auto rounded-md border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Docente ID
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rol
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Base
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Plus
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {segmento.liquidaciones.map((liq: LiquidacionRead) => (
                <tr
                  key={liq.id}
                  className={liq.estado === 'Cerrada' ? 'opacity-70' : ''}
                >
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">
                    {liq.usuario_id.slice(0, 8)}…
                  </td>
                  <td className="px-4 py-2 text-gray-700">{liq.rol}</td>
                  <td className="px-4 py-2 text-right text-gray-700">
                    {formatARS(liq.base_monto)}
                  </td>
                  <td className="px-4 py-2 text-right text-gray-700">
                    {formatARS(liq.plus_monto)}
                  </td>
                  <td className="px-4 py-2 text-right font-medium text-gray-900">
                    {formatARS(liq.total_monto)}
                  </td>
                  <td className="px-4 py-2">
                    <EstadoBadge estado={liq.estado} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export function LiquidacionSegmentadaView({ data }: Props) {
  return (
    <div className="space-y-6">
      {/* KPI Header */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
          <p className="text-xs text-blue-600 font-medium uppercase tracking-wider mb-1">
            Total sin factura
          </p>
          <p className="text-2xl font-bold text-blue-900">
            {formatARS(data.total_sin_factura)}
          </p>
        </div>
        <div className="bg-purple-50 border border-purple-100 rounded-lg p-4">
          <p className="text-xs text-purple-600 font-medium uppercase tracking-wider mb-1">
            Total con factura
          </p>
          <p className="text-2xl font-bold text-purple-900">
            {formatARS(data.total_con_factura)}
          </p>
        </div>
      </div>

      {/* Three segments */}
      <div className="space-y-6 divide-y divide-gray-100">
        <SegmentoTable titulo="General" segmento={data.general} />
        <div className="pt-4">
          <SegmentoTable titulo="NEXO" segmento={data.nexo} />
        </div>
        <div className="pt-4">
          <SegmentoTable titulo="Facturantes" segmento={data.facturantes} />
        </div>
      </div>
    </div>
  )
}
