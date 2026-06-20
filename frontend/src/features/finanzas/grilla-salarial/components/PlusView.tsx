/**
 * PlusView.tsx — Table of plus with inline edit/delete.
 *
 * Actions: edit (opens inline form), delete (with confirmation dialog).
 * Button "Nuevo plus" opens create form.
 */

import { useState } from 'react'
import {
  usePlus,
  useCreatePlus,
  useUpdatePlus,
  useDeletePlus,
} from '../hooks/useGrillaSalarial'
import { PlusForm } from './PlusForm'
import type { Plus } from '../types'
import type { PlusData } from '../types/schemas'

export function PlusView() {
  const { data, isLoading, error } = usePlus()
  const createMutation = useCreatePlus()
  const updateMutation = useUpdatePlus()
  const deleteMutation = useDeletePlus()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  function handleCreate(formData: PlusData) {
    createMutation.mutate(
      {
        clave: formData.clave,
        rol: formData.rol,
        descripcion: formData.descripcion ?? null,
        monto: formData.monto,
        desde: formData.desde,
        hasta: formData.hasta ?? null,
      },
      { onSuccess: () => setShowCreateForm(false) },
    )
  }

  function handleUpdate(id: string, formData: PlusData) {
    updateMutation.mutate(
      {
        id,
        data: {
          clave: formData.clave,
          rol: formData.rol,
          descripcion: formData.descripcion ?? null,
          monto: formData.monto,
          desde: formData.desde,
          hasta: formData.hasta ?? null,
        },
      },
      { onSuccess: () => setEditingId(null) },
    )
  }

  function handleDelete(id: string) {
    deleteMutation.mutate(id, { onSuccess: () => setDeletingId(null) })
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500 py-4">Cargando...</p>
  }

  if (error) {
    return (
      <p className="text-sm text-red-600 py-4">Error al cargar plus.</p>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => { setShowCreateForm(true); setEditingId(null) }}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
        >
          + Nuevo plus
        </button>
      </div>

      {showCreateForm && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Nuevo plus</h3>
          <PlusForm
            onSubmit={handleCreate}
            onCancel={() => setShowCreateForm(false)}
            isPending={createMutation.isPending}
          />
        </div>
      )}

      {!data || data.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-sm">No hay plus configurados.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Clave
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rol
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Descripción
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Monto
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Vigencia
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {data.map((p: Plus) => (
                <>
                  <tr key={p.id}>
                    <td className="px-4 py-2 font-mono text-xs font-medium text-gray-900">
                      {p.clave}
                    </td>
                    <td className="px-4 py-2 text-gray-700">{p.rol}</td>
                    <td className="px-4 py-2 text-gray-500">{p.descripcion ?? '—'}</td>
                    <td className="px-4 py-2 text-right text-gray-700">
                      {parseFloat(p.monto).toLocaleString('es-AR', {
                        style: 'currency',
                        currency: 'ARS',
                      })}
                    </td>
                    <td className="px-4 py-2 text-gray-600 text-xs">
                      {p.desde} → {p.hasta ?? '∞'}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => { setEditingId(p.id); setShowCreateForm(false) }}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Editar
                        </button>
                        {deletingId === p.id ? (
                          <span className="flex gap-2 text-xs">
                            <button
                              type="button"
                              onClick={() => handleDelete(p.id)}
                              disabled={deleteMutation.isPending}
                              className="text-red-600 hover:underline disabled:opacity-50"
                            >
                              Confirmar
                            </button>
                            <button
                              type="button"
                              onClick={() => setDeletingId(null)}
                              className="text-gray-500 hover:underline"
                            >
                              Cancelar
                            </button>
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setDeletingId(p.id)}
                            className="text-xs text-red-600 hover:underline"
                          >
                            Eliminar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {editingId === p.id && (
                    <tr key={`${p.id}-edit`}>
                      <td colSpan={6} className="px-4 py-3 bg-gray-50">
                        <PlusForm
                          initial={p}
                          onSubmit={(formData) => handleUpdate(p.id, formData)}
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
