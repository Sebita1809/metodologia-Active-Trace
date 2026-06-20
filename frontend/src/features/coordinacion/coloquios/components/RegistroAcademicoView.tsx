/**
 * RegistroAcademicoView.tsx — Academic results view per convocatoria.
 *
 * Selector de convocatoria → tabla de resultados (alumno, instancia, nota).
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useEvaluaciones, useResultados } from '../hooks/useColoquios'

export function RegistroAcademicoView() {
  const { data: evaluaciones = [] } = useEvaluaciones()
  const [evaluacionId, setEvaluacionId] = useState<string | null>(null)
  const { data: resultados = [], isLoading } = useResultados(evaluacionId)

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Seleccioná una convocatoria
        </label>
        <select
          className="border border-gray-300 rounded px-3 py-2 text-sm"
          value={evaluacionId ?? ''}
          onChange={(e) => setEvaluacionId(e.target.value || null)}
        >
          <option value="">-- Elegir convocatoria --</option>
          {evaluaciones.map((ev) => (
            <option key={ev.id} value={ev.id}>
              {ev.materia_id} — Instancia {ev.instancia}
            </option>
          ))}
        </select>
      </div>

      {evaluacionId && (
        isLoading ? (
          <p className="text-sm text-gray-500">Cargando resultados...</p>
        ) : resultados.length === 0 ? (
          <div className="text-center py-6 text-sm text-gray-500">
            Sin resultados registrados para esta convocatoria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Alumno ID</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">Instancia</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">Nota</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {resultados.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-2 font-mono text-xs text-gray-500">{r.alumno_id}</td>
                    <td className="px-4 py-2 text-right text-gray-700">{r.instancia}</td>
                    <td className="px-4 py-2 text-right text-gray-700">
                      {r.nota !== null ? r.nota : '—'}
                    </td>
                    <td className="px-4 py-2">
                      <span className={r.aprobado ? 'text-green-700 font-medium' : 'text-red-600 font-medium'}>
                        {r.aprobado ? 'Aprobado' : 'Desaprobado'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  )
}
