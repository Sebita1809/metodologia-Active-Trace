/**
 * CarrerasView.tsx — Table of carreras with edit/toggle estado actions.
 *
 * Columns: código, nombre, estado. Acciones: editar, toggle estado.
 * Button "Nueva carrera" opens create form.
 */

import { useState } from 'react'
import {
  useCarreras,
  useCreateCarrera,
  useUpdateCarrera,
} from '../hooks/useEstructura'
import { CarreraForm } from './CarreraForm'
import type { Carrera, EstadoCarrera } from '../types'
import type { CarreraData } from '../types/schemas'

function EstadoBadge({ estado }: { estado: EstadoCarrera }) {
  return (
    <span
      className={[
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
        estado === 'Activa'
          ? 'bg-green-100 text-green-700'
          : 'bg-gray-100 text-gray-500',
      ].join(' ')}
    >
      {estado}
    </span>
  )
}

export function CarrerasView() {
  const { data, isLoading, error } = useCarreras()
  const createMutation = useCreateCarrera()
  const updateMutation = useUpdateCarrera()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  function handleCreate(formData: CarreraData) {
    createMutation.mutate(formData, { onSuccess: () => setShowCreateForm(false) })
  }

  function handleUpdate(id: string, formData: CarreraData) {
    updateMutation.mutate({ id, data: formData }, { onSuccess: () => setEditingId(null) })
  }

  function handleToggleEstado(carrera: Carrera) {
    const nuevoEstado: EstadoCarrera =
      carrera.estado === 'Activa' ? 'Inactiva' : 'Activa'
    updateMutation.mutate({ id: carrera.id, data: { estado: nuevoEstado } })
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500 py-4">Cargando...</p>
  }

  if (error) {
    return <p className="text-sm text-red-600 py-4">Error al cargar carreras.</p>
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => { setShowCreateForm(true); setEditingId(null) }}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
        >
          + Nueva carrera
        </button>
      </div>

      {showCreateForm && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Nueva carrera</h3>
          <CarreraForm
            onSubmit={handleCreate}
            onCancel={() => setShowCreateForm(false)}
            isPending={createMutation.isPending}
          />
        </div>
      )}

      {!data || data.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-sm">No hay carreras registradas.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Código
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Nombre
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
              {data.map((c: Carrera) => (
                <>
                  <tr key={c.id}>
                    <td className="px-4 py-2 font-mono text-xs font-medium text-gray-900">
                      {c.codigo}
                    </td>
                    <td className="px-4 py-2 text-gray-700">{c.nombre}</td>
                    <td className="px-4 py-2">
                      <EstadoBadge estado={c.estado} />
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => { setEditingId(c.id); setShowCreateForm(false) }}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleEstado(c)}
                          disabled={updateMutation.isPending}
                          className="text-xs text-gray-600 hover:underline disabled:opacity-50"
                        >
                          {c.estado === 'Activa' ? 'Desactivar' : 'Activar'}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {editingId === c.id && (
                    <tr key={`${c.id}-edit`}>
                      <td colSpan={4} className="px-4 py-3 bg-gray-50">
                        <CarreraForm
                          initial={c}
                          onSubmit={(formData) => handleUpdate(c.id, formData)}
                          onCancel={() => setEditingId(null)}
                          isPending={updateMutation.isPending}
                        />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
