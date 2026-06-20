/**
 * FechasAcademicasView.tsx — View of academic dates with table/calendar toggle.
 *
 * Two views: tabla (materia, tipo, instancia, fecha, cohorte, título) and calendario mensual visual.
 * Filter requires materia + cohorte to be selected.
 */

import { useState } from 'react'
import {
  useFechasAcademicas,
  useCreateFecha,
  useDeleteFecha,
} from '../hooks/useProgramasFechas'
import { useCohortes, useMaterias } from '@/features/admin/estructura/hooks/useEstructura'
import { FechaAcademicaForm } from './FechaAcademicaForm'
import { CalendarioEvaluaciones } from './CalendarioEvaluaciones'
import type { FechaAcademicaFilters } from '../types'
import type { FechaAcademicaData } from '../types/schemas'

type ViewMode = 'tabla' | 'calendario'

export function FechasAcademicasView() {
  const { data: materias } = useMaterias()
  const { data: cohortes } = useCohortes()

  const [filters, setFilters] = useState<FechaAcademicaFilters | null>(null)
  const [materiaId, setMateriaId] = useState('')
  const [cohorteId, setCohorteId] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('tabla')
  const [showForm, setShowForm] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const currentDate = new Date()
  const [calMes, setCalMes] = useState(currentDate.getMonth() + 1)
  const [calAnio, setCalAnio] = useState(currentDate.getFullYear())

  const { data: fechas, isLoading, error } = useFechasAcademicas(filters)
  const createMutation = useCreateFecha()
  const deleteMutation = useDeleteFecha()

  function handleApplyFilter() {
    if (materiaId && cohorteId) {
      setFilters({ materia_id: materiaId, cohorte_id: cohorteId })
    }
  }

  function handleCreate(formData: FechaAcademicaData) {
    createMutation.mutate(
      {
        materia_id: formData.materia_id,
        cohorte_id: formData.cohorte_id,
        tipo: formData.tipo,
        numero: formData.numero,
        fecha: formData.fecha,
        titulo: formData.titulo,
        periodo: formData.periodo ?? null,
      },
      { onSuccess: () => setShowForm(false) },
    )
  }

  function handleDelete(id: string) {
    deleteMutation.mutate(id, { onSuccess: () => setDeletingId(null) })
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-end bg-gray-50 p-4 rounded-lg border border-gray-200">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Materia</label>
          <select
            value={materiaId}
            onChange={(e) => setMateriaId(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Seleccionar materia...</option>
            {materias?.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Cohorte</label>
          <select
            value={cohorteId}
            onChange={(e) => setCohorteId(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Seleccionar cohorte...</option>
            {cohortes?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={handleApplyFilter}
          disabled={!materiaId || !cohorteId}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          Buscar
        </button>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <div className="flex border border-gray-300 rounded-md overflow-hidden">
          <button
            type="button"
            onClick={() => setViewMode('tabla')}
            className={[
              'px-3 py-1.5 text-sm font-medium',
              viewMode === 'tabla'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50',
            ].join(' ')}
          >
            Tabla
          </button>
          <button
            type="button"
            onClick={() => setViewMode('calendario')}
            className={[
              'px-3 py-1.5 text-sm font-medium',
              viewMode === 'calendario'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50',
            ].join(' ')}
          >
            Calendario
          </button>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
        >
          + Nueva fecha
        </button>
      </div>

      {showForm && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Nueva fecha académica</h3>
          <FechaAcademicaForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
            isPending={createMutation.isPending}
          />
        </div>
      )}

      {!filters && (
        <p className="text-sm text-gray-500 py-4">
          Seleccioná materia y cohorte para ver las fechas.
        </p>
      )}

      {isLoading && <p className="text-sm text-gray-500 py-4">Cargando...</p>}
      {error && <p className="text-sm text-red-600 py-4">Error al cargar fechas.</p>}

      {fechas && viewMode === 'tabla' && (
        <div className="overflow-x-auto rounded-md border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fecha
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  N°
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Título
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {fechas.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-500">
                    No hay fechas registradas para esta combinación.
                  </td>
                </tr>
              )}
              {fechas.map((f) => (
                <tr key={f.id}>
                  <td className="px-4 py-2 text-gray-700">{f.fecha}</td>
                  <td className="px-4 py-2 text-gray-700 capitalize">{f.tipo}</td>
                  <td className="px-4 py-2 text-gray-700">{f.numero}</td>
                  <td className="px-4 py-2 text-gray-700">{f.titulo}</td>
                  <td className="px-4 py-2">
                    {deletingId === f.id ? (
                      <span className="flex gap-2 text-xs">
                        <button
                          type="button"
                          onClick={() => handleDelete(f.id)}
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
                        onClick={() => setDeletingId(f.id)}
                        className="text-xs text-red-600 hover:underline"
                      >
                        Eliminar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {fechas && viewMode === 'calendario' && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                if (calMes === 1) { setCalMes(12); setCalAnio((y) => y - 1) }
                else setCalMes((m) => m - 1)
              }}
              className="px-2 py-1 text-sm text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
            >
              ←
            </button>
            <button
              type="button"
              onClick={() => {
                if (calMes === 12) { setCalMes(1); setCalAnio((y) => y + 1) }
                else setCalMes((m) => m + 1)
              }}
              className="px-2 py-1 text-sm text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
            >
              →
            </button>
          </div>
          <CalendarioEvaluaciones fechas={fechas} mes={calMes} anio={calAnio} />
        </div>
      )}
    </div>
  )
}
