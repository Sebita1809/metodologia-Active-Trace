/**
 * ProgramasView.tsx — Table of programas de materia with filters by carrera and cohorte.
 *
 * Filters: carrera, cohorte. Botón "Subir programa" opens create form.
 */

import { useState } from 'react'
import {
  useProgramas,
  useCreatePrograma,
} from '../hooks/useProgramasFechas'
import { ProgramaForm } from './ProgramaForm'
import { useCarreras, useCohortes } from '@/features/admin/estructura/hooks/useEstructura'
import type { ProgramaFilters } from '../types'
import type { ProgramaData } from '../types/schemas'

export function ProgramasView() {
  const [filters, setFilters] = useState<ProgramaFilters>({})
  const [showForm, setShowForm] = useState(false)

  const { data: carreras } = useCarreras()
  const { data: cohortes } = useCohortes()
  const { data: programas, isLoading, error } = useProgramas(filters)
  const createMutation = useCreatePrograma()

  function handleCreate(formData: ProgramaData) {
    createMutation.mutate(
      {
        materia_id: formData.materia_id,
        carrera_id: formData.carrera_id,
        cohorte_id: formData.cohorte_id,
        titulo: formData.titulo,
        referencia_archivo: formData.referencia_archivo,
      },
      { onSuccess: () => setShowForm(false) },
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-4 items-end justify-between">
        <div className="flex gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">Carrera</label>
            <select
              value={filters.carrera_id ?? ''}
              onChange={(e) =>
                setFilters((f) => ({ ...f, carrera_id: e.target.value || undefined }))
              }
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todas</option>
              {carreras?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.codigo}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">Cohorte</label>
            <select
              value={filters.cohorte_id ?? ''}
              onChange={(e) =>
                setFilters((f) => ({ ...f, cohorte_id: e.target.value || undefined }))
              }
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              {cohortes?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
        >
          + Subir programa
        </button>
      </div>

      {showForm && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Nuevo programa de materia</h3>
          <ProgramaForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
            isPending={createMutation.isPending}
          />
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-500 py-4">Cargando...</p>}
      {error && <p className="text-sm text-red-600 py-4">Error al cargar programas.</p>}

      {programas && programas.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p className="text-sm">No hay programas cargados.</p>
        </div>
      )}

      {programas && programas.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Título
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Materia
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Archivo
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cargado
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {programas.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-2 font-medium text-gray-900">{p.titulo}</td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">
                    {p.materia_id.slice(0, 8)}…
                  </td>
                  <td className="px-4 py-2">
                    <a
                      href={p.referencia_archivo}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Ver archivo
                    </a>
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs">
                    {new Date(p.created_at).toLocaleDateString('es-AR')}
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
