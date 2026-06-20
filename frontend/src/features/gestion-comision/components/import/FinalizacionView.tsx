/**
 * components/import/FinalizacionView.tsx — Detección de entregas sin corregir + export.
 *
 * - POST /api/calificaciones/finalizacion-preview with the LMS finalization report
 * - Shows table of uncorrected submissions
 * - Exports table as CSV (client-side Blob download)
 *
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useFinalizacionPreview } from '../../hooks/useCalificaciones'
import type { FinalizacionItem } from '../../types/calificaciones'
import { EmptyState } from '../EmptyState'

interface FinalizacionViewProps {
  asignacionId: string
}

function exportToCSV(items: FinalizacionItem[]) {
  const header = 'Email alumno,Actividad'
  const rows = items.map(
    (item) => `"${item.alumno_email}","${item.actividad}"`,
  )
  const csv = [header, ...rows].join('\n')

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'entregas-sin-corregir.csv'
  link.click()
  URL.revokeObjectURL(url)
}

export function FinalizacionView({ asignacionId }: FinalizacionViewProps) {
  const [items, setItems] = useState<FinalizacionItem[] | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const previewMutation = useFinalizacionPreview()

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setItems(null)
    setUploadError(null)

    try {
      const result = await previewMutation.mutateAsync({
        file,
        asignacion_id: asignacionId,
      })
      setItems(result.items)
    } catch {
      setUploadError(
        'Error al procesar el reporte. Verificá el formato e intentá de nuevo.',
      )
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-base font-semibold text-gray-900">
        Entregas sin corregir
      </h2>

      <div>
        <label
          htmlFor="file-finalizacion"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Reporte de finalización (LMS export)
        </label>
        <input
          id="file-finalizacion"
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileChange}
          className="block text-sm text-gray-700 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
      </div>

      {previewMutation.isPending && (
        <p className="text-sm text-gray-500">Procesando reporte...</p>
      )}

      {uploadError && (
        <div className="rounded-md bg-red-50 p-3">
          <p className="text-sm text-red-700">{uploadError}</p>
        </div>
      )}

      {items !== null && items.length === 0 && (
        <EmptyState
          title="Sin entregas pendientes"
          description="No se detectaron entregas sin corregir en el reporte."
        />
      )}

      {items !== null && items.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600">
              {items.length} entrega{items.length !== 1 ? 's' : ''} sin corregir
            </p>
            <button
              type="button"
              onClick={() => exportToCSV(items)}
              className="rounded bg-gray-100 px-3 py-1 text-sm font-medium text-gray-700 hover:bg-gray-200"
            >
              Exportar CSV
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">
                    Email alumno
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">
                    Actividad
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {items.map((item, idx) => (
                  <tr key={idx}>
                    <td className="px-4 py-2 text-gray-600">{item.alumno_email}</td>
                    <td className="px-4 py-2 text-gray-600">{item.actividad}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
