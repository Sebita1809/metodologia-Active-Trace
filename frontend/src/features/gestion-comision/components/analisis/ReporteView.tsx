/**
 * components/analisis/ReporteView.tsx — Quick report metrics for the comision.
 *
 * Consumes GET /api/v1/analisis/reporte.
 * Shows informative state when tiene_datos is false.
 *
 * < 200 LOC, no `any`, no class components.
 */

import { useReporte } from '../../hooks/useAnalisis'
import { EmptyState } from '../EmptyState'

interface ReporteViewProps {
  asignacionId: string
}

export function ReporteView({ asignacionId }: ReporteViewProps) {
  const { data, isLoading, isError } = useReporte(asignacionId)

  if (isLoading) return <p className="text-sm text-gray-500">Cargando reporte...</p>

  if (isError) {
    return <p className="text-sm text-red-600">Error al cargar el reporte.</p>
  }

  if (!data || !data.tiene_datos) {
    return (
      <EmptyState
        title="Sin datos"
        description="Importá calificaciones y seleccioná actividades para ver el reporte de la comisión."
      />
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-gray-900">Reporte rápido</h2>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg bg-white border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{data.total_alumnos}</p>
          <p className="mt-1 text-xs text-gray-500">Alumnos</p>
        </div>
        <div className="rounded-lg bg-white border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-red-600">{data.total_atrasados}</p>
          <p className="mt-1 text-xs text-gray-500">Atrasados</p>
        </div>
        <div className="rounded-lg bg-white border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-blue-600">
            {data.pct_aprobacion_general.toFixed(1)} %
          </p>
          <p className="mt-1 text-xs text-gray-500">Aprobación general</p>
        </div>
        <div className="rounded-lg bg-white border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{data.total_actividades}</p>
          <p className="mt-1 text-xs text-gray-500">Actividades</p>
        </div>
      </div>
    </div>
  )
}
