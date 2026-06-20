/**
 * ConvocatoriasView.tsx — Table of active evaluaciones with operational metrics.
 *
 * Actions per row: "Importar alumnos".
 * Global action: "Nueva convocatoria".
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useEvaluaciones } from '../hooks/useColoquios'
import { ConvocatoriaForm } from './ConvocatoriaForm'
import { ImportarAlumnosDialog } from './ImportarAlumnosDialog'

export function ConvocatoriasView() {
  const { data: evaluaciones = [], isLoading } = useEvaluaciones()
  const [showForm, setShowForm] = useState(false)
  const [importandoId, setImportandoId] = useState<string | null>(null)

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => setShowForm((v) => !v)}
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
        >
          Nueva convocatoria
        </button>
      </div>

      {showForm && (
        <div className="border border-gray-200 rounded p-4 bg-white">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-semibold text-gray-800">Nueva convocatoria</h3>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">✕</button>
          </div>
          <ConvocatoriaForm onSuccess={() => setShowForm(false)} onCancel={() => setShowForm(false)} />
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando convocatorias...</p>
      ) : evaluaciones.length === 0 ? (
        <div className="text-center py-8 text-sm text-gray-500">
          Sin convocatorias activas. Creá la primera.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Materia</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Instancia</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">Convocados</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">Reservas</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">Cupos libres</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {evaluaciones.map((ev) => (
                <tr key={ev.id}>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{ev.materia_id}</td>
                  <td className="px-4 py-2 text-gray-700">{ev.instancia}</td>
                  <td className="px-4 py-2 text-right text-gray-700">{ev.total_convocados}</td>
                  <td className="px-4 py-2 text-right text-gray-700">{ev.reservas_activas}</td>
                  <td className="px-4 py-2 text-right text-gray-700">{ev.cupos_libres}</td>
                  <td className="px-4 py-2">
                    <button
                      onClick={() => setImportandoId(ev.id)}
                      className="text-blue-600 hover:underline text-xs"
                    >
                      Importar alumnos
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {importandoId && (
        <ImportarAlumnosDialog
          evaluacionId={importandoId}
          onClose={() => setImportandoId(null)}
        />
      )}
    </div>
  )
}
