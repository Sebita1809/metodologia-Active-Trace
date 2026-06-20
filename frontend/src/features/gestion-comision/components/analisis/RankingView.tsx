/**
 * components/analisis/RankingView.tsx — Ranking of approved activities per student.
 *
 * Consumes GET /api/v1/analisis/ranking.
 * < 200 LOC, no `any`, no class components.
 */

import { useRanking } from '../../hooks/useAnalisis'
import { EmptyState } from '../EmptyState'

interface RankingViewProps {
  asignacionId: string
}

export function RankingView({ asignacionId }: RankingViewProps) {
  const { data, isLoading, isError } = useRanking(asignacionId)

  if (isLoading) return <p className="text-sm text-gray-500">Cargando ranking...</p>

  if (isError) {
    return <p className="text-sm text-red-600">Error al cargar el ranking.</p>
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="Sin datos de ranking"
        description="Importá calificaciones para ver el ranking de actividades aprobadas."
      />
    )
  }

  return (
    <div className="space-y-3">
      <h2 className="text-base font-semibold text-gray-900">
        Ranking de actividades aprobadas
      </h2>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">
                Posición
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Nombre</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Apellidos</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">
                Aprobadas
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.items.map((item, idx) => (
              <tr key={item.alumno_id}>
                <td className="px-4 py-2 text-gray-500">{idx + 1}</td>
                <td className="px-4 py-2 text-gray-700">{item.nombre}</td>
                <td className="px-4 py-2 text-gray-700">{item.apellidos}</td>
                <td className="px-4 py-2 text-right font-medium text-blue-700">
                  {item.aprobadas}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
