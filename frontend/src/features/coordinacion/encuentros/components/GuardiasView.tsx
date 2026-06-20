/**
 * GuardiasView.tsx — Table of guardias with filters, register, and export.
 *
 * Filters: tutor (asignacion_id), fecha rango.
 * Actions: "Registrar guardia", "Exportar CSV".
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useGuardias } from '../hooks/useEncuentros'
import { exportarGuardias } from '../services/guardiasService'
import { GuardiaForm } from './GuardiaForm'
import type { GuardiaFilters } from '../types'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function GuardiasView() {
  const [filters, setFilters] = useState<GuardiaFilters>({})
  const [showForm, setShowForm] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [asignacionIdForm, setAsignacionIdForm] = useState('')
  const { data: guardias = [], isLoading } = useGuardias(filters)

  async function handleExport() {
    setExporting(true)
    try {
      const blob = await exportarGuardias(filters)
      downloadBlob(blob, 'guardias.csv')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Actions and filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Fecha desde</label>
          <input
            type="date"
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            value={filters.fecha_desde ?? ''}
            onChange={(e) => setFilters((f) => ({ ...f, fecha_desde: e.target.value || undefined }))}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Fecha hasta</label>
          <input
            type="date"
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            value={filters.fecha_hasta ?? ''}
            onChange={(e) => setFilters((f) => ({ ...f, fecha_hasta: e.target.value || undefined }))}
          />
        </div>
        <div className="ml-auto flex gap-2">
          <button
            onClick={() => setShowForm((v) => !v)}
            className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
          >
            Registrar guardia
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
          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Asignación (UUID)
            </label>
            <input
              value={asignacionIdForm}
              onChange={(e) => setAsignacionIdForm(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm w-full"
              placeholder="UUID de la asignación"
            />
          </div>
          {asignacionIdForm && (
            <GuardiaForm
              asignacionId={asignacionIdForm}
              onSuccess={() => { setShowForm(false); setAsignacionIdForm('') }}
              onCancel={() => { setShowForm(false); setAsignacionIdForm('') }}
            />
          )}
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando guardias...</p>
      ) : guardias.length === 0 ? (
        <div className="text-center py-8 text-sm text-gray-500">
          Sin guardias registradas.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Cubierto por</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Día</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Horario</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Comentarios</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {guardias.map((g) => (
                <tr key={g.id}>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{g.cubierto_por}</td>
                  <td className="px-4 py-2 text-gray-700">{g.dia}</td>
                  <td className="px-4 py-2 text-gray-700">{g.horario}</td>
                  <td className="px-4 py-2 text-gray-600">{g.estado}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{g.comentarios ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
