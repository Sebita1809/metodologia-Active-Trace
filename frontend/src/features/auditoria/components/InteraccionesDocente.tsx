/**
 * InteraccionesDocente.tsx — Table of usage metrics per docente and materia.
 *
 * Columns: actor_id, materia_id, total (interacciones).
 */

import type { InteraccionesDocenteMateriaItem } from '../types'

interface InteraccionesDocenteProps {
  items: InteraccionesDocenteMateriaItem[]
}

export function InteraccionesDocente({ items }: InteraccionesDocenteProps) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-4">Sin datos de interacciones.</p>
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
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Materia
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Interacciones
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {items.map((item: InteraccionesDocenteMateriaItem, i) => (
            <tr key={`${item.actor_id}-${item.materia_id ?? 'null'}-${i}`}>
              <td className="px-4 py-2 font-mono text-xs text-gray-500">
                {item.actor_id.slice(0, 8)}…
              </td>
              <td className="px-4 py-2 font-mono text-xs text-gray-500">
                {item.materia_id ? `${item.materia_id.slice(0, 8)}…` : '—'}
              </td>
              <td className="px-4 py-2 text-right font-medium text-gray-900">
                {item.total}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
