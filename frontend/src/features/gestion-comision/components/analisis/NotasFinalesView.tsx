/**
 * components/analisis/NotasFinalesView.tsx — Final grades grouped by student.
 *
 * Consumes GET /api/v1/analisis/notas-finales.
 * < 200 LOC, no `any`, no class components.
 */

import { useNotasFinales } from '../../hooks/useAnalisis'
import { EmptyState } from '../EmptyState'

interface NotasFinalesViewProps {
  asignacionId: string
}

export function NotasFinalesView({ asignacionId }: NotasFinalesViewProps) {
  const { data, isLoading, isError } = useNotasFinales(asignacionId)

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando notas finales...</p>
  }

  if (isError) {
    return <p className="text-sm text-red-600">Error al cargar las notas finales.</p>
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="Sin datos de notas finales"
        description="Importá calificaciones para ver las notas finales."
      />
    )
  }

  return (
    <div className="space-y-3">
      <h2 className="text-base font-semibold text-gray-900">Notas finales</h2>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Nombre</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Apellidos</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Aprobadas</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Total</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">% Aprobación</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.items.map((item) => (
              <tr key={item.alumno_id}>
                <td className="px-4 py-2 text-gray-700">{item.nombre}</td>
                <td className="px-4 py-2 text-gray-700">{item.apellidos}</td>
                <td className="px-4 py-2 text-right text-gray-600">{item.aprobadas}</td>
                <td className="px-4 py-2 text-right text-gray-600">
                  {item.total_actividades}
                </td>
                <td className="px-4 py-2 text-right font-medium text-blue-700">
                  {item.porcentaje_aprobacion.toFixed(1)} %
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
