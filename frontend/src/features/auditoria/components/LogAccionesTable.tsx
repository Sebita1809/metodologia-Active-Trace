/**
 * LogAccionesTable.tsx — Table of recent N audit log actions.
 *
 * Columns: fecha/hora, usuario (actor_id), materia, acción, registros_afectados, ip, agente.
 */

import type { LogAuditoriaItem } from '../types'

interface LogAccionesTableProps {
  items: LogAuditoriaItem[]
}

export function LogAccionesTable({ items }: LogAccionesTableProps) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-4">Sin acciones registradas.</p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-md border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Fecha/Hora
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Usuario
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Acción
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Filas
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              IP
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {items.map((item: LogAuditoriaItem) => (
            <tr key={item.id}>
              <td className="px-4 py-2 text-gray-600 text-xs whitespace-nowrap">
                {new Date(item.fecha_hora).toLocaleString('es-AR', {
                  day: '2-digit',
                  month: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </td>
              <td className="px-4 py-2 font-mono text-xs text-gray-500">
                {item.actor_id.slice(0, 8)}…
                {item.impersonado_id && (
                  <span className="text-amber-500 ml-1" title="Impersonación">
                    👤
                  </span>
                )}
              </td>
              <td className="px-4 py-2 text-gray-700 font-medium">
                {item.accion}
                {item.materia_id && (
                  <span className="ml-2 text-xs text-gray-400">
                    ({item.materia_id.slice(0, 6)}…)
                  </span>
                )}
              </td>
              <td className="px-4 py-2 text-right text-gray-500">
                {item.filas_afectadas}
              </td>
              <td className="px-4 py-2 font-mono text-xs text-gray-400">
                {item.ip ?? '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
