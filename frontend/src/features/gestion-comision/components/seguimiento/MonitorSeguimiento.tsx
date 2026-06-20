/**
 * components/seguimiento/MonitorSeguimiento.tsx — Filterable activity status monitor.
 *
 * Reutiliza datos de notas-finales y reporte para presentar una vista filtrable.
 * Filters: alumno name, min cumplido %.
 * For COORDINADOR/ADMIN: additionally shows fecha_desde / fecha_hasta date range filters (C-23 F2.9).
 *
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useAuth } from '@/features/auth/context/AuthContext'
import { useNotasFinales, useReporte } from '../../hooks/useAnalisis'
import { EmptyState } from '../EmptyState'

interface MonitorSeguimientoProps {
  asignacionId: string
}

export function MonitorSeguimiento({ asignacionId }: MonitorSeguimientoProps) {
  const { claims } = useAuth()
  const [filtroAlumno, setFiltroAlumno] = useState('')
  const [minCumplido, setMinCumplido] = useState<number | ''>('')
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')

  const roles = claims?.roles ?? []
  const showDateFilters =
    roles.includes('COORDINADOR') || roles.includes('ADMIN')

  const reporteQuery = useReporte(asignacionId)
  const notasQuery = useNotasFinales(
    asignacionId,
    showDateFilters
      ? { fecha_desde: fechaDesde || undefined, fecha_hasta: fechaHasta || undefined }
      : undefined,
  )

  const isLoading = reporteQuery.isLoading || notasQuery.isLoading

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando monitor de seguimiento...</p>
  }

  const sinDatos = !reporteQuery.data?.tiene_datos

  if (sinDatos) {
    return (
      <EmptyState
        title="Sin datos de seguimiento"
        description="Importá calificaciones para ver el seguimiento de actividades por alumno."
      />
    )
  }

  const items = notasQuery.data?.items ?? []

  // Apply filters
  const filteredItems = items.filter((item) => {
    const nombre = `${item.nombre} ${item.apellidos}`.toLowerCase()
    const matchAlumno =
      filtroAlumno === '' || nombre.includes(filtroAlumno.toLowerCase())

    const matchMin =
      minCumplido === '' || item.porcentaje_aprobacion >= minCumplido

    return matchAlumno && matchMin
  })

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-gray-900">Monitor de seguimiento</h2>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div>
          <input
            type="text"
            placeholder="Buscar alumno..."
            value={filtroAlumno}
            onChange={(e) => setFiltroAlumno(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
          />
        </div>

        <div className="flex items-center gap-2">
          <label
            htmlFor="min-cumplido"
            className="text-sm text-gray-700 whitespace-nowrap"
          >
            Mínimo cumplido (%)
          </label>
          <input
            id="min-cumplido"
            type="number"
            min={0}
            max={100}
            value={minCumplido}
            onChange={(e) =>
              setMinCumplido(e.target.value === '' ? '' : Number(e.target.value))
            }
            className="w-20 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Date range filters — visible only for COORDINADOR / ADMIN (C-23 F2.9) */}
        {showDateFilters && (
          <>
            <div className="flex items-center gap-2">
              <label
                htmlFor="fecha-desde"
                className="text-sm text-gray-700 whitespace-nowrap"
              >
                Desde
              </label>
              <input
                id="fecha-desde"
                type="date"
                value={fechaDesde}
                onChange={(e) => setFechaDesde(e.target.value)}
                className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <label
                htmlFor="fecha-hasta"
                className="text-sm text-gray-700 whitespace-nowrap"
              >
                Hasta
              </label>
              <input
                id="fecha-hasta"
                type="date"
                value={fechaHasta}
                onChange={(e) => setFechaHasta(e.target.value)}
                className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </>
        )}
      </div>

      {filteredItems.length === 0 ? (
        <EmptyState
          title="Sin resultados"
          description="No hay alumnos que coincidan con los filtros aplicados."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Nombre</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Apellidos</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">Aprobadas</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">Total</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">% Cumplido</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.map((item) => (
                <tr key={item.alumno_id}>
                  <td className="px-4 py-2 text-gray-700">{item.nombre}</td>
                  <td className="px-4 py-2 text-gray-700">{item.apellidos}</td>
                  <td className="px-4 py-2 text-right text-gray-600">{item.aprobadas}</td>
                  <td className="px-4 py-2 text-right text-gray-600">
                    {item.total_actividades}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <span
                      className={
                        item.porcentaje_aprobacion >= 60
                          ? 'text-green-700 font-medium'
                          : 'text-red-600 font-medium'
                      }
                    >
                      {item.porcentaje_aprobacion.toFixed(1)} %
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
