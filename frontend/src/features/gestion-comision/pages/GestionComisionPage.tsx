/**
 * pages/GestionComisionPage.tsx — Main orchestration page for the gestion-comision feature.
 *
 * Manages:
 * - Comision selector (asignacion_id context)
 * - Informative state when no comision selected
 * - Sub-views: importacion, umbral, atrasados, ranking, notas finales, reporte, monitor, comunicacion
 * - 403 fail-closed: shows access denied when backend rejects
 *
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useAuth } from '@/features/auth/context/AuthContext'
import { isAccessDeniedError } from '@/shared/services/api'
import { EmptyState } from '../components/EmptyState'
import { TablaAtrasados } from '../components/analisis/TablaAtrasados'
import { RankingView } from '../components/analisis/RankingView'
import { NotasFinalesView } from '../components/analisis/NotasFinalesView'
import { ReporteView } from '../components/analisis/ReporteView'
import { ImportacionView } from '../components/import/ImportacionView'
import { UmbralView } from '../components/umbral/UmbralView'
import { MonitorSeguimiento } from '../components/seguimiento/MonitorSeguimiento'
import { ComunicacionView } from '../components/comunicacion/ComunicacionView'
import { useAsignaciones } from '../hooks/useAsignaciones'
import { useReporte } from '../hooks/useAnalisis'

type TabId =
  | 'importacion'
  | 'umbral'
  | 'atrasados'
  | 'ranking'
  | 'notas-finales'
  | 'reporte'
  | 'monitor'
  | 'comunicacion'

const TABS: { id: TabId; label: string }[] = [
  { id: 'importacion', label: 'Importación' },
  { id: 'umbral', label: 'Umbral' },
  { id: 'atrasados', label: 'Atrasados' },
  { id: 'ranking', label: 'Ranking' },
  { id: 'notas-finales', label: 'Notas finales' },
  { id: 'reporte', label: 'Reporte' },
  { id: 'monitor', label: 'Monitor' },
  { id: 'comunicacion', label: 'Comunicación' },
]

export function GestionComisionPage() {
  const { claims } = useAuth()
  const [asignacionId, setAsignacionId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('importacion')

  const { data: asignaciones, isLoading: loadingAsig } = useAsignaciones(
    claims?.sub,
  )

  // Detect if the currently selected asignacion triggers a 403
  const reporteQuery = useReporte(asignacionId)
  const is403 = isAccessDeniedError(reporteQuery.error)

  if (loadingAsig) {
    return (
      <div className="p-6 text-sm text-gray-500">Cargando comisiones...</div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <label
          htmlFor="comision-select"
          className="text-sm font-medium text-gray-700"
        >
          Comisión
        </label>
        <select
          id="comision-select"
          aria-label="comisión"
          className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={asignacionId ?? ''}
          onChange={(e) => {
            const val = e.target.value
            setAsignacionId(val === '' ? null : val)
          }}
        >
          <option value="">Seleccioná una comisión</option>
          {asignaciones?.map((a) => (
            <option key={a.id} value={a.id}>
              {a.materia_id ?? a.id}{' '}
              {a.cohorte_id ? `(Cohorte: ${a.cohorte_id})` : ''}
            </option>
          ))}
        </select>
      </div>

      {!asignacionId && (
        <EmptyState
          title="Seleccioná una comisión"
          description="Elegí una comisión del selector para ver y gestionar sus datos académicos."
        />
      )}

      {asignacionId && is403 && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">Acceso denegado</p>
          <p className="mt-1 text-sm text-red-600">
            No tenés permisos para acceder a esta comisión.
          </p>
        </div>
      )}

      {asignacionId && !is403 && (
        <>
          {/* Tab navigation */}
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex gap-4 overflow-x-auto">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={[
                    'whitespace-nowrap border-b-2 pb-3 px-1 text-sm font-medium transition-colors',
                    activeTab === tab.id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                  ].join(' ')}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab content */}
          <div>
            {activeTab === 'importacion' && (
              <ImportacionView asignacionId={asignacionId} />
            )}
            {activeTab === 'umbral' && (
              <UmbralView asignacionId={asignacionId} />
            )}
            {activeTab === 'atrasados' && (
              <TablaAtrasados asignacionId={asignacionId} />
            )}
            {activeTab === 'ranking' && (
              <RankingView asignacionId={asignacionId} />
            )}
            {activeTab === 'notas-finales' && (
              <NotasFinalesView asignacionId={asignacionId} />
            )}
            {activeTab === 'reporte' && (
              <ReporteView asignacionId={asignacionId} />
            )}
            {activeTab === 'monitor' && (
              <MonitorSeguimiento asignacionId={asignacionId} />
            )}
            {activeTab === 'comunicacion' && (
              <ComunicacionView asignacionId={asignacionId} />
            )}
          </div>
        </>
      )}
    </div>
  )
}
