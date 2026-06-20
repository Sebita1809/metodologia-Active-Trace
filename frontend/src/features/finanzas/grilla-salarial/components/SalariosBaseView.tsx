/**
 * SalariosBaseView.tsx — Table of salarios base with inline edit/delete.
 *
 * Actions: edit (opens inline form), delete (with confirmation).
 * Button "Nuevo salario base" opens create form.
 */

import { useState } from 'react'
import {
  useSalariosBase,
  useCreateSalarioBase,
  useUpdateSalarioBase,
  useDeleteSalarioBase,
} from '../hooks/useGrillaSalarial'
import { SalarioBaseForm } from './SalarioBaseForm'
import type { SalarioBase } from '../types'
import type { SalarioBaseData } from '../types/schemas'

export function SalariosBaseView() {
  const { data, isLoading, error } = useSalariosBase()
  const createMutation = useCreateSalarioBase()
  const updateMutation = useUpdateSalarioBase()
  const deleteMutation = useDeleteSalarioBase()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  function handleCreate(formData: SalarioBaseData) {
    createMutation.mutate(
      { rol: formData.rol, monto: formData.monto, desde: formData.desde, hasta: formData.hasta ?? null },
      { onSuccess: () => setShowCreateForm(false) },
    )
  }

  function handleUpdate(id: string, formData: SalarioBaseData) {
    updateMutation.mutate(
      { id, data: { rol: formData.rol, monto: formData.monto, desde: formData.desde, hasta: formData.hasta ?? null } },
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
      <p className="text-sm text-red-600 py-4">
        Error al cargar salarios base.
      </p>
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
          + Nuevo salario base
        </button>
      </div>

      {showCreateForm && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Nuevo salario base</h3>
          <SalarioBaseForm
            onSubmit={handleCreate}
            onCancel={() => setShowCreateForm(false)}
            isPending={createMutation.isPending}
          />
        </div>
      )}

      {!data || data.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-sm">No hay salarios base configurados.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rol
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Monto
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Desde
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Hasta
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {data.map((sb: SalarioBase) => (
                <>
                  <tr key={sb.id}>
                    <td className="px-4 py-2 font-medium text-gray-900">{sb.rol}</td>
                    <td className="px-4 py-2 text-right text-gray-700">
                      {parseFloat(sb.monto).toLocaleString('es-AR', {
                        style: 'currency',
                        currency: 'ARS',
                      })}
                    </td>
                    <td className="px-4 py-2 text-gray-700">{sb.desde}</td>
                    <td className="px-4 py-2 text-gray-500">{sb.hasta ?? '—'}</td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => { setEditingId(sb.id); setShowCreateForm(false) }}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Editar
                        </button>
                        {deletingId === sb.id ? (
                          <span className="flex gap-2 text-xs">
                            <button
                              type="button"
                              onClick={() => handleDelete(sb.id)}
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
                            onClick={() => setDeletingId(sb.id)}
                            className="text-xs text-red-600 hover:underline"
                          >
                            Eliminar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {editingId === sb.id && (
                    <tr key={`${sb.id}-edit`}>
                      <td colSpan={5} className="px-4 py-3 bg-gray-50">
                        <SalarioBaseForm
                          initial={sb}
                          onSubmit={(formData) => handleUpdate(sb.id, formData)}
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
