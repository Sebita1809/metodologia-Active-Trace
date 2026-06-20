/**
 * MonitorGeneralTable.tsx — Paginated table of alumnos with activity status.
 *
 * Button "Exportar CSV".
 * < 200 LOC, no `any`, no class components.
 */

import { exportarMonitor } from '../services/monitorGeneralService'
import type { MonitorAlumno, MonitorGeneralFilters } from '../types'
import { useState } from 'react'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const ESTADO_BADGE: Record<string, string> = {
  al_dia: 'bg-green-50 text-green-700',
  atrasado: 'bg-red-50 text-red-700',
  sin_datos: 'bg-gray-50 text-gray-500',
}

interface MonitorGeneralTableProps {
  items: MonitorAlumno[]
  total: number
  filters: MonitorGeneralFilters
}

export function MonitorGeneralTable({
  items,
  total,
  filters,
}: MonitorGeneralTableProps) {
  const [exporting, setExporting] = useState(false)

  async function handleExport() {
    setExporting(true)
    try {
      const blob = await exportarMonitor(filters)
      downloadBlob(blob, 'monitor-general.csv')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">{total} alumnos</p>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="bg-gray-100 text-gray-700 px-3 py-1.5 rounded text-sm hover:bg-gray-200 disabled:opacity-50"
        >
          {exporting ? 'Exportando...' : 'Exportar CSV'}
        </button>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-8 text-sm text-gray-500">
          Sin datos de actividades para el tenant.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Alumno</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Email</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Comisión</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Regional</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">Aprobadas</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">Total</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">%</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((item) => (
                <tr key={`${item.alumno_id}-${item.materia_id}`}>
                  <td className="px-4 py-2 text-gray-800">
                    {item.nombre} {item.apellidos}
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{item.email}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{item.comision ?? '—'}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{item.regional ?? '—'}</td>
                  <td className="px-4 py-2 text-right text-gray-700">
                    {item.actividades_aprobadas}
                  </td>
                  <td className="px-4 py-2 text-right text-gray-700">
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
                      {item.porcentaje_aprobacion.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${ESTADO_BADGE[item.estado_actividad] ?? ''}`}
                    >
                      {item.estado_actividad.replace('_', ' ')}
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
