/**
 * MateriasView.tsx — Table of materias with edit/toggle estado.
 *
 * Columns: nombre, código, estado.
 * Acciones: editar, toggle activo/inactivo.
 * Botón "Nueva materia" opens create form.
 */

import { useState } from 'react'
import {
  useMaterias,
  useCreateMateria,
  useUpdateMateria,
} from '../hooks/useEstructura'
import { MateriaForm } from './MateriaForm'
import type { Materia, EstadoMateria } from '../types'
import type { MateriaData } from '../types/schemas'

function EstadoBadge({ estado }: { estado: EstadoMateria }) {
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

export function MateriasView() {
  const { data, isLoading, error } = useMaterias()
  const createMutation = useCreateMateria()
  const updateMutation = useUpdateMateria()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  function handleCreate(formData: MateriaData) {
    createMutation.mutate(
      {
        nombre: formData.nombre,
        codigo: formData.codigo ?? null,
        estado: formData.estado,
      },
      { onSuccess: () => setShowCreateForm(false) },
    )
  }

  function handleUpdate(id: string, formData: MateriaData) {
    updateMutation.mutate(
      {
        id,
        data: {
          nombre: formData.nombre,
          codigo: formData.codigo ?? null,
          estado: formData.estado,
        },
      },
      { onSuccess: () => setEditingId(null) },
    )
  }

  function handleToggleEstado(materia: Materia) {
    const nuevoEstado: EstadoMateria =
      materia.estado === 'Activa' ? 'Inactiva' : 'Activa'
    updateMutation.mutate({ id: materia.id, data: { estado: nuevoEstado } })
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500 py-4">Cargando...</p>
  }

  if (error) {
    return <p className="text-sm text-red-600 py-4">Error al cargar materias.</p>
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => { setShowCreateForm(true); setEditingId(null) }}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
        >
          + Nueva materia
        </button>
      </div>

      {showCreateForm && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Nueva materia</h3>
          <MateriaForm
            onSubmit={handleCreate}
            onCancel={() => setShowCreateForm(false)}
            isPending={createMutation.isPending}
          />
        </div>
      )}

      {!data || data.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-sm">No hay materias registradas.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Nombre
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Código
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
              {data.map((m: Materia) => (
                <>
                  <tr key={m.id}>
                    <td className="px-4 py-2 font-medium text-gray-900">{m.nombre}</td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-500">
                      {m.codigo ?? '—'}
                    </td>
                    <td className="px-4 py-2">
                      <EstadoBadge estado={m.estado} />
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => { setEditingId(m.id); setShowCreateForm(false) }}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleEstado(m)}
                          disabled={updateMutation.isPending}
                          className="text-xs text-gray-600 hover:underline disabled:opacity-50"
                        >
                          {m.estado === 'Activa' ? 'Desactivar' : 'Activar'}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {editingId === m.id && (
                    <tr key={`${m.id}-edit`}>
                      <td colSpan={4} className="px-4 py-3 bg-gray-50">
                        <MateriaForm
                          initial={m}
                          onSubmit={(formData) => handleUpdate(m.id, formData)}
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
