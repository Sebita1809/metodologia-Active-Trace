/**
 * AsignacionesView.tsx — Filterable table of asignaciones + export CSV.
 *
 * Filters: materia, carrera, cohorte, docente (usuario_id), rol.
 * Actions: "Nueva asignación" (modal form), "Exportar CSV".
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useAsignaciones } from '../hooks/useEquipos'
import { exportarEquipo } from '../services/asignacionesService'
import { AsignacionForm } from './AsignacionForm'
import type { AsignacionFilters } from '../types'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function AsignacionesView() {
  const [filters, setFilters] = useState<AsignacionFilters>({})
  const [showForm, setShowForm] = useState(false)
  const [exporting, setExporting] = useState(false)
  const { data: asignaciones = [], isLoading } = useAsignaciones(filters)

  async function handleExport() {
    setExporting(true)
    try {
      const blob = await exportarEquipo(filters)
      downloadBlob(blob, 'equipo-docente.csv')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Materia (UUID)</label>
          <input
            className="border border-gray-300 rounded px-3 py-1.5 text-sm w-44"
            value={filters.materia_id ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, materia_id: e.target.value || undefined }))
            }
            placeholder="UUID materia"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Rol</label>
          <select
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            value={filters.rol ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, rol: e.target.value || undefined }))
            }
          >
            <option value="">Todos</option>
            {['TUTOR', 'PROFESOR', 'COORDINADOR'].map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <div className="ml-auto flex gap-2">
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
          >
            Nueva asignación
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="bg-gray-100 text-gray-700 px-3 py-1.5 rounded text-sm hover:bg-gray-200 disabled:opacity-50"
          >
            {exporting ? 'Exportando...' : 'Exportar CSV'}
          </button>
        </div>
      </div>

      {/* Form */}
      {showForm && (
        <div className="border border-gray-200 rounded p-4 bg-white">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-semibold text-gray-800">Nueva asignación</h3>
            <button
              onClick={() => setShowForm(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
          <AsignacionForm onSuccess={() => setShowForm(false)} />
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando asignaciones...</p>
      ) : asignaciones.length === 0 ? (
        <div className="text-center py-8 text-sm text-gray-500">
          Sin asignaciones para los criterios seleccionados.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Docente ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Rol</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Materia</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Desde</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Hasta</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {asignaciones.map((a) => (
                <tr key={a.id}>
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">{a.usuario_id}</td>
                  <td className="px-4 py-2 text-gray-700">{a.rol}</td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">{a.materia_id ?? '—'}</td>
                  <td className="px-4 py-2 text-gray-700">{a.desde}</td>
                  <td className="px-4 py-2 text-gray-700">{a.hasta ?? '—'}</td>
                  <td className="px-4 py-2">
                    <span
                      className={
                        a.estado_vigencia === 'Vigente'
                          ? 'text-green-700 font-medium'
                          : 'text-gray-400'
                      }
                    >
                      {a.estado_vigencia}
                    </span>
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
