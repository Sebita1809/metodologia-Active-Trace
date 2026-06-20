/**
 * EncuentrosTenantView.tsx — Table of all tenant encuentros (admin view).
 *
 * Columns: docente, materia, fecha, horario, estado, enlace grabación.
 * Filters: docente, mes (YYYY-MM).
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useEncuentrosTenant } from '../hooks/useEncuentros'
import type { EncuentroFilters } from '../types'

const ESTADO_BADGE: Record<string, string> = {
  Programado: 'bg-blue-50 text-blue-700',
  Realizado: 'bg-green-50 text-green-700',
  Cancelado: 'bg-red-50 text-red-700',
}

export function EncuentrosTenantView() {
  const [filters, setFilters] = useState<EncuentroFilters>({})
  const { data: encuentros = [], isLoading } = useEncuentrosTenant(filters)

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Docente (UUID)</label>
          <input
            className="border border-gray-300 rounded px-3 py-1.5 text-sm w-44"
            placeholder="UUID docente"
            value={filters.docente_id ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, docente_id: e.target.value || undefined }))
            }
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Mes (YYYY-MM)</label>
          <input
            type="month"
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            value={filters.mes ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, mes: e.target.value || undefined }))
            }
          />
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando encuentros...</p>
      ) : encuentros.length === 0 ? (
        <div className="text-center py-8 text-sm text-gray-500">
          Sin encuentros registrados.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Docente</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Materia</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Fecha</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Horario</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Grabación</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {encuentros.map((enc) => (
                <tr key={enc.id}>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{enc.docente_id}</td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{enc.materia_id ?? '—'}</td>
                  <td className="px-4 py-2 text-gray-700">{enc.fecha}</td>
                  <td className="px-4 py-2 text-gray-600">
                    {enc.horario_inicio ?? '—'}{enc.horario_fin ? ` - ${enc.horario_fin}` : ''}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${ESTADO_BADGE[enc.estado] ?? ''}`}>
                      {enc.estado}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {enc.enlace_grabacion ? (
                      <a
                        href={enc.enlace_grabacion}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline text-xs"
                      >
                        Ver
                      </a>
                    ) : (
                      <span className="text-gray-400 text-xs">—</span>
                    )}
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
