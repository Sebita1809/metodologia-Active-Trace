/**
 * MisTareasView.tsx — View for the authenticated user's own tasks.
 *
 * Shows tasks assigned to the current user.
 * Inline state selector (Abierta/En progreso/Completada).
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useMisTareas, useUpdateTarea } from '../hooks/useTareas'
import { TareaHiloView } from './TareaHiloView'
import type { EstadoTarea, Tarea } from '../types'

const ESTADOS: EstadoTarea[] = ['Abierta', 'En progreso', 'Completada']

const ESTADO_BADGE: Record<EstadoTarea, string> = {
  Abierta: 'bg-gray-100 text-gray-700',
  'En progreso': 'bg-blue-50 text-blue-700',
  Completada: 'bg-green-50 text-green-700',
  Cerrada: 'bg-gray-50 text-gray-400',
}

export function MisTareasView() {
  const { data: tareas = [], isLoading } = useMisTareas()
  const updateTarea = useUpdateTarea()
  const [selectedTarea, setSelectedTarea] = useState<Tarea | null>(null)

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando tareas...</p>
  }

  if (tareas.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-gray-500">
        Sin tareas asignadas.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Tarea</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Materia</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Asignador</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {tareas.map((tarea) => (
              <tr key={tarea.id}>
                <td className="px-4 py-2">
                  <p className="font-medium text-gray-800">{tarea.titulo}</p>
                  <p className="text-xs text-gray-400 line-clamp-1">{tarea.descripcion}</p>
                </td>
                <td className="px-4 py-2 font-mono text-xs text-gray-500">
                  {tarea.materia_id ?? '—'}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-gray-500">
                  {tarea.asignada_por}
                </td>
                <td className="px-4 py-2">
                  <select
                    value={tarea.estado}
                    onChange={(e) =>
                      updateTarea.mutate({
                        id: tarea.id,
                        body: { estado: e.target.value as EstadoTarea },
                      })
                    }
                    disabled={tarea.estado === 'Cerrada'}
                    className={`text-xs px-2 py-1 rounded border-0 focus:ring-1 focus:ring-blue-500 ${ESTADO_BADGE[tarea.estado]}`}
                  >
                    {ESTADOS.map((e) => (
                      <option key={e} value={e}>
                        {e}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => setSelectedTarea(selectedTarea?.id === tarea.id ? null : tarea)}
                    className="text-blue-600 hover:underline text-xs"
                  >
                    Ver hilo
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedTarea && (
        <div className="border border-gray-200 rounded p-4 bg-white">
          <TareaHiloView tarea={selectedTarea} onClose={() => setSelectedTarea(null)} />
        </div>
      )}
    </div>
  )
}
