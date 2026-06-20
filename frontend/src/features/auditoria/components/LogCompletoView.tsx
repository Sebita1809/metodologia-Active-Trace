/**
 * LogCompletoView.tsx — Full audit log, visible only to ADMIN.
 *
 * Same structure as LogAccionesTable but without record limit.
 * Includes filters: desde, hasta, materia_id, usuario_id, accion, estado.
 */

import { useState } from 'react'
import { useLogCompleto } from '../hooks/useAuditoria'
import { LogAccionesTable } from './LogAccionesTable'
import type { AuditoriaFilters } from '../types'

export function LogCompletoView() {
  const [filters, setFilters] = useState<AuditoriaFilters>({ limit: 200, offset: 0 })
  const [desdeInput, setDesdeInput] = useState('')
  const [hastaInput, setHastaInput] = useState('')
  const [accionInput, setAccionInput] = useState('')

  const { data, isLoading, error } = useLogCompleto(filters)

  function handleApplyFilters() {
    setFilters({
      ...(desdeInput ? { desde: desdeInput } : {}),
      ...(hastaInput ? { hasta: hastaInput } : {}),
      ...(accionInput ? { accion: accionInput } : {}),
      limit: 200,
      offset: 0,
    })
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-end bg-gray-50 p-4 rounded-lg border border-gray-200">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Desde</label>
          <input
            type="date"
            value={desdeInput}
            onChange={(e) => setDesdeInput(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Hasta</label>
          <input
            type="date"
            value={hastaInput}
            onChange={(e) => setHastaInput(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Acción</label>
          <input
            type="text"
            value={accionInput}
            onChange={(e) => setAccionInput(e.target.value)}
            placeholder="ej: importar_calificaciones"
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          type="button"
          onClick={handleApplyFilters}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
        >
          Filtrar
        </button>
      </div>

      {isLoading && (
        <p className="text-sm text-gray-500 py-4">Cargando log...</p>
      )}
      {error && (
        <p className="text-sm text-red-600 py-4">Error al cargar el log de auditoría.</p>
      )}
      {data && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500">
            {data.total} registros totales — mostrando {data.items.length}
          </p>
          <LogAccionesTable items={data.items} />
        </div>
      )}
    </div>
  )
}
