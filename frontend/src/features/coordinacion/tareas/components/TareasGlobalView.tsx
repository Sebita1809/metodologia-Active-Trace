/**
 * TareasGlobalView.tsx — Global view of all tenant tasks (COORDINADOR/ADMIN).
 *
 * Filters: docente asignado, asignador, materia, estado, búsqueda libre.
 * Actions: cambiar estado, devolver tarea con observación.
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useTareas, useUpdateTarea } from '../hooks/useTareas'
import { TareaHiloView } from './TareaHiloView'
import type { EstadoTarea, Tarea, TareaFilters } from '../types'

const ESTADOS: EstadoTarea[] = ['Abierta', 'En progreso', 'Completada', 'Cerrada']

export function TareasGlobalView() {
  const [filters, setFilters] = useState<TareaFilters>({})
  const [selectedTarea, setSelectedTarea] = useState<Tarea | null>(null)
  const [devolviendoId, setDevolviendoId] = useState<string | null>(null)
  const [observacion, setObservacion] = useState('')

  const { data: tareas = [], isLoading } = useTareas(filters)
  const updateTarea = useUpdateTarea()

  function handleDevolver(tareaId: string) {
    if (!observacion.trim()) return
    updateTarea.mutate(
      { id: tareaId, body: { estado: 'En progreso', observacion: observacion.trim() } },
      { onSuccess: () => { setDevolviendoId(null); setObservacion('') } },
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          className="border border-gray-300 rounded px-3 py-1.5 text-sm w-44"
          placeholder="Buscar..."
          value={filters.q ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value || undefined }))}
        />
        <select
          className="border border-gray-300 rounded px-3 py-1.5 text-sm"
          value={filters.estado ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, estado: (e.target.value as EstadoTarea) || undefined }))}
        >
          <option value="">Todos los estados</option>
          {ESTADOS.map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
        <button
          onClick={() => setFilters({})}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Limpiar filtros
        </button>
      </div>

      {/* Table */}
      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando tareas...</p>
      ) : tareas.length === 0 ? (
        <div className="text-center py-8 text-sm text-gray-500">
          Sin tareas que coincidan con los filtros.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Tarea</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Asignada a</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Por</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tareas.map((tarea) => (
                <tr key={tarea.id}>
                  <td className="px-4 py-2">
                    <p className="font-medium text-gray-800">{tarea.titulo}</p>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{tarea.asignada_a}</td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{tarea.asignada_por}</td>
                  <td className="px-4 py-2">
                    <select
                      value={tarea.estado}
                      onChange={(e) =>
                        updateTarea.mutate({
                          id: tarea.id,
                          body: { estado: e.target.value as EstadoTarea },
                        })
                      }
                      className="text-xs border border-gray-300 rounded px-2 py-1"
                    >
                      {ESTADOS.map((e) => <option key={e} value={e}>{e}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2">
                      <button
                        onClick={() => setSelectedTarea(selectedTarea?.id === tarea.id ? null : tarea)}
                        className="text-blue-600 hover:underline text-xs"
                      >
                        Hilo
                      </button>
                      <button
                        onClick={() => setDevolviendoId(devolviendoId === tarea.id ? null : tarea.id)}
                        className="text-yellow-600 hover:underline text-xs"
                      >
                        Devolver
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Devolver dialog */}
      {devolviendoId && (
        <div className="border border-yellow-200 bg-yellow-50 rounded p-4 space-y-2 max-w-lg">
          <p className="text-sm font-medium text-yellow-800">Devolver tarea al docente</p>
          <textarea
            value={observacion}
            onChange={(e) => setObservacion(e.target.value)}
            rows={3}
            placeholder="Observación obligatoria..."
            className="w-full border border-yellow-300 rounded px-3 py-2 text-sm"
          />
          <div className="flex gap-2">
            <button
              onClick={() => handleDevolver(devolviendoId)}
              disabled={!observacion.trim() || updateTarea.isPending}
              className="bg-yellow-600 text-white px-3 py-1.5 rounded text-sm hover:bg-yellow-700 disabled:opacity-50"
            >
              Devolver
            </button>
            <button
              onClick={() => { setDevolviendoId(null); setObservacion('') }}
              className="bg-gray-200 text-gray-700 px-3 py-1.5 rounded text-sm hover:bg-gray-300"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {selectedTarea && (
        <div className="border border-gray-200 rounded p-4 bg-white">
          <TareaHiloView tarea={selectedTarea} onClose={() => setSelectedTarea(null)} />
        </div>
      )}
    </div>
  )
}
