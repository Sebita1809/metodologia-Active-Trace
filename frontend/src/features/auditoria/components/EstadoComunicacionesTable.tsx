/**
 * EstadoComunicacionesTable.tsx — Table of communication states per docente.
 *
 * Columns: actor_id, Pendiente, Enviando, OK (enviado), Fallido, Cancelado.
 */

import type { ComunicacionesPorDocenteItem } from '../types'

interface EstadoComunicacionesTableProps {
  items: ComunicacionesPorDocenteItem[]
}

export function EstadoComunicacionesTable({ items }: EstadoComunicacionesTableProps) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-4">Sin datos de comunicaciones.</p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-md border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Docente
            </th>
            <th className="px-4 py-2 text-center text-xs font-medium text-yellow-600 uppercase tracking-wider">
              Pendiente
            </th>
            <th className="px-4 py-2 text-center text-xs font-medium text-blue-600 uppercase tracking-wider">
              Enviando
            </th>
            <th className="px-4 py-2 text-center text-xs font-medium text-green-600 uppercase tracking-wider">
              OK
            </th>
            <th className="px-4 py-2 text-center text-xs font-medium text-red-600 uppercase tracking-wider">
              Fallido
            </th>
            <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Cancelado
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {items.map((item: ComunicacionesPorDocenteItem) => (
            <tr key={item.actor_id}>
              <td className="px-4 py-2 font-mono text-xs text-gray-500">
                {item.actor_id.slice(0, 8)}…
              </td>
              <td className="px-4 py-2 text-center text-yellow-700">
                {item.pendiente}
              </td>
              <td className="px-4 py-2 text-center text-blue-700">
                {item.enviando}
              </td>
              <td className="px-4 py-2 text-center text-green-700 font-medium">
                {item.enviado}
              </td>
              <td className="px-4 py-2 text-center text-red-700">
                {item.fallido}
              </td>
              <td className="px-4 py-2 text-center text-gray-500">
                {item.cancelado}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
