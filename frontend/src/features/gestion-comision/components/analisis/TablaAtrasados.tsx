/**
 * components/analisis/TablaAtrasados.tsx — Table of atrasados students.
 *
 * Consumes GET /api/v1/analisis/atrasados.
 * Shows informative empty state when no atrasados.
 *
 * Also used as selection source for comunicacion flow.
 *
 * < 200 LOC, no `any`, no class components.
 */

import { useAtrasados } from '../../hooks/useAnalisis'
import type { AlumnoAtrasado } from '../../types/analisis'
import { EmptyState } from '../EmptyState'

interface TablaAtrasadosProps {
  asignacionId: string
  /** Optional selection mode for comunicacion flow */
  selectable?: boolean
  selectedIds?: Set<string>
  onToggle?: (alumno: AlumnoAtrasado) => void
}

export function TablaAtrasados({
  asignacionId,
  selectable = false,
  selectedIds,
  onToggle,
}: TablaAtrasadosProps) {
  const { data, isLoading, isError } = useAtrasados(asignacionId)

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando atrasados...</p>
  }

  if (isError) {
    return (
      <p className="text-sm text-red-600">
        Error al cargar los alumnos atrasados.
      </p>
    )
  }

  if (!data || data.atrasados.length === 0) {
    return (
      <EmptyState
        title="Sin alumnos atrasados"
        description={
          data?.sin_padron
            ? 'No hay padrón importado para esta comisión.'
            : 'Todos los alumnos están al día con sus actividades.'
        }
      />
    )
  }

  return (
    <div className="space-y-3">
      <h2 className="text-base font-semibold text-gray-900">Alumnos atrasados</h2>
      {data.sin_padron && (
        <p className="text-xs text-amber-600">
          Atención: sin padrón importado — los datos pueden ser incompletos.
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {selectable && (
                <th className="px-4 py-3 text-left font-medium text-gray-700 w-10">
                  <span className="sr-only">Seleccionar</span>
                </th>
              )}
              <th className="px-4 py-3 text-left font-medium text-gray-700">Nombre</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Apellidos</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">
                Actividades faltantes
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">
                Actividades reprobadas
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.atrasados.map((alumno) => (
              <tr
                key={alumno.alumno_id}
                className={selectable ? 'cursor-pointer hover:bg-gray-50' : ''}
                onClick={selectable && onToggle ? () => onToggle(alumno) : undefined}
              >
                {selectable && (
                  <td className="px-4 py-2">
                    <input
                      type="checkbox"
                      checked={selectedIds?.has(alumno.alumno_id) ?? false}
                      onChange={() => onToggle?.(alumno)}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded border-gray-300 text-blue-600"
                      aria-label={`Seleccionar ${alumno.nombre} ${alumno.apellidos}`}
                    />
                  </td>
                )}
                <td className="px-4 py-2 text-gray-700">{alumno.nombre}</td>
                <td className="px-4 py-2 text-gray-700">{alumno.apellidos}</td>
                <td className="px-4 py-2 text-gray-600">
                  {alumno.actividades_faltantes.join(', ') || '—'}
                </td>
                <td className="px-4 py-2 text-gray-600">
                  {alumno.actividades_reprobadas.join(', ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
