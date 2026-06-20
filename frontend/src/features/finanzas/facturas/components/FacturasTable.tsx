/**
 * FacturasTable.tsx — Table of comprobantes (facturas).
 *
 * Columns: fecha_carga, docente (usuario_id), período, detalle,
 *          archivo (link), tamaño, estado (badge), datos_pago.
 * Action inline: "Cambiar estado".
 */

import { useState } from 'react'
import { useCambiarEstadoFactura } from '../hooks/useFacturas'
import type { Factura, EstadoFactura } from '../types'

const MESES_LABEL = [
  '', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
]

function EstadoBadge({ estado }: { estado: EstadoFactura }) {
  return (
    <span
      className={[
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
        estado === 'Abonada'
          ? 'bg-green-100 text-green-700'
          : 'bg-yellow-100 text-yellow-700',
      ].join(' ')}
    >
      {estado}
    </span>
  )
}

interface FacturasTableProps {
  facturas: Factura[]
}

export function FacturasTable({ facturas }: FacturasTableProps) {
  const cambiarEstadoMutation = useCambiarEstadoFactura()
  const [changingId, setChangingId] = useState<string | null>(null)

  function handleCambiarEstado(id: string, estadoActual: EstadoFactura) {
    const nuevoEstado: EstadoFactura =
      estadoActual === 'Pendiente' ? 'Abonada' : 'Pendiente'
    setChangingId(id)
    cambiarEstadoMutation.mutate(
      { id, data: { nuevo_estado: nuevoEstado } },
      { onSettled: () => setChangingId(null) },
    )
  }

  if (facturas.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-sm">No hay facturas con los filtros seleccionados.</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-md border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Fecha carga
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Docente
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Período
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Detalle
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Monto
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Estado
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Acciones
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {facturas.map((f: Factura) => (
            <tr key={f.id}>
              <td className="px-4 py-2 text-gray-600 text-xs">
                {new Date(f.created_at).toLocaleDateString('es-AR')}
              </td>
              <td className="px-4 py-2 font-mono text-xs text-gray-500">
                {f.usuario_id.slice(0, 8)}…
              </td>
              <td className="px-4 py-2 text-gray-700">
                {MESES_LABEL[f.periodo_mes]} {f.periodo_anio}
              </td>
              <td className="px-4 py-2 text-gray-700 max-w-xs truncate">
                {f.detalle}
              </td>
              <td className="px-4 py-2 text-right font-medium text-gray-900">
                {parseFloat(f.monto).toLocaleString('es-AR', {
                  style: 'currency',
                  currency: 'ARS',
                })}
              </td>
              <td className="px-4 py-2">
                <EstadoBadge estado={f.estado} />
              </td>
              <td className="px-4 py-2">
                <button
                  type="button"
                  onClick={() => handleCambiarEstado(f.id, f.estado)}
                  disabled={changingId === f.id}
                  className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                >
                  {changingId === f.id
                    ? 'Cambiando...'
                    : f.estado === 'Pendiente'
                    ? 'Marcar abonada'
                    : 'Marcar pendiente'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
