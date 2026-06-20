/**
 * AgendaReservasView.tsx — Agenda of reservas for a selected convocatoria.
 *
 * Selector de convocatoria → tabla de reservas agrupadas por día.
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useEvaluaciones, useReservas } from '../hooks/useColoquios'

export function AgendaReservasView() {
  const { data: evaluaciones = [] } = useEvaluaciones()
  const [evaluacionId, setEvaluacionId] = useState<string | null>(null)
  const { data: reservas = [], isLoading } = useReservas(evaluacionId)

  // Group reservas by day
  const byDay = reservas.reduce<Record<string, typeof reservas>>((acc, r) => {
    const day = r.fecha_reservada.split('T')[0] ?? r.fecha_reservada
    if (!acc[day]) acc[day] = []
    acc[day].push(r)
    return acc
  }, {})

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
          <p className="text-sm text-gray-500">Cargando reservas...</p>
        ) : reservas.length === 0 ? (
          <div className="text-center py-6 text-sm text-gray-500">
            Sin reservas activas para esta convocatoria.
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(byDay).map(([day, dayReservas]) => (
              <div key={day}>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">{day}</h4>
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-gray-600">Alumno ID</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-600">Turno</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {dayReservas.map((r) => (
                      <tr key={r.id}>
                        <td className="px-4 py-2 font-mono text-xs text-gray-500">{r.alumno_id}</td>
                        <td className="px-4 py-2 text-right text-gray-700">{r.turno}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  )
}
