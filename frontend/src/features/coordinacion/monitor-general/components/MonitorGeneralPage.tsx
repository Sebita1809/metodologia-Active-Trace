/**
 * MonitorGeneralPage.tsx — Global student activity monitor page.
 *
 * Filters: materia, regional, comisión, búsqueda libre, estado de actividad, criterio.
 * Button "Limpiar filtros".
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useMonitorGeneral } from '../hooks/useMonitorGeneral'
import { MonitorGeneralTable } from './MonitorGeneralTable'
import type { EstadoActividad, MonitorGeneralFilters } from '../types'

const ESTADOS_ACTIVIDAD: { value: EstadoActividad | ''; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'al_dia', label: 'Al día' },
  { value: 'atrasado', label: 'Atrasado' },
  { value: 'sin_datos', label: 'Sin datos' },
]

export function MonitorGeneralPage() {
  const [filters, setFilters] = useState<MonitorGeneralFilters>({})
  const { data, isLoading } = useMonitorGeneral(filters)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-900">Monitor general</h1>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Materia (UUID)</label>
          <input
            className="border border-gray-300 rounded px-3 py-1.5 text-sm w-40"
            placeholder="UUID materia"
            value={filters.materia_id ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, materia_id: e.target.value || undefined }))
            }
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Regional</label>
          <input
            className="border border-gray-300 rounded px-3 py-1.5 text-sm w-32"
            placeholder="Regional"
            value={filters.regional ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, regional: e.target.value || undefined }))
            }
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Comisión</label>
          <input
            className="border border-gray-300 rounded px-3 py-1.5 text-sm w-32"
            placeholder="Comisión"
            value={filters.comision ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, comision: e.target.value || undefined }))
            }
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Búsqueda</label>
          <input
            className="border border-gray-300 rounded px-3 py-1.5 text-sm w-40"
            placeholder="Nombre o email"
            value={filters.q ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, q: e.target.value || undefined }))
            }
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Estado</label>
          <select
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            value={filters.estado_actividad ?? ''}
            onChange={(e) =>
              setFilters((f) => ({
                ...f,
                estado_actividad: (e.target.value as EstadoActividad) || undefined,
              }))
            }
          >
            {ESTADOS_ACTIVIDAD.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={() => setFilters({})}
          className="text-sm text-gray-500 hover:text-gray-700 px-3 py-1.5"
        >
          Limpiar filtros
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando monitor...</p>
      ) : (
        <MonitorGeneralTable
          items={data?.items ?? []}
          total={data?.total ?? 0}
          filters={filters}
        />
      )}
    </div>
  )
}
