/**
 * LiquidacionesPage.tsx — Main page for FINANZAS: liquidaciones with tabs.
 *
 * Tabs: "Período actual", "Historial", "Grilla salarial" (link/shortcut).
 * <200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FiltrosPeriodoForm } from '../components/FiltrosPeriodoForm'
import { LiquidacionSegmentadaView } from '../components/LiquidacionSegmentadaView'
import { HistorialLiquidacionesView } from '../components/HistorialLiquidacionesView'
import {
  useLiquidaciones,
  useCerrarLiquidacion,
  useCalcularLiquidacion,
  useExportarLiquidacion,
} from '../hooks/useLiquidaciones'
import { CerrarLiquidacionDialog } from '../components/CerrarLiquidacionDialog'
import type { LiquidacionFilters } from '../types'
import type { LiquidacionFiltrosData } from '../types/schemas'

type Tab = 'periodo' | 'historial'

const TABS: { id: Tab; label: string }[] = [
  { id: 'periodo', label: 'Período actual' },
  { id: 'historial', label: 'Historial' },
]

export function LiquidacionesPage() {
  const [activeTab, setActiveTab] = useState<Tab>('periodo')
  const [filters, setFilters] = useState<LiquidacionFilters | null>(null)
  const [showCerrarDialog, setShowCerrarDialog] = useState(false)

  const { data: periodoData, isLoading, error } = useLiquidaciones(filters)
  const calcularMutation = useCalcularLiquidacion(filters)
  const cerrarMutation = useCerrarLiquidacion(filters)
  const exportarMutation = useExportarLiquidacion()

  function handleFilter(data: LiquidacionFiltrosData) {
    setFilters({ cohorte_id: data.cohorte_id, mes: data.mes, anio: data.anio })
  }

  function handleCalcular() {
    if (!filters) return
    calcularMutation.mutate({
      cohorte_id: filters.cohorte_id,
      mes: filters.mes,
      anio: filters.anio,
    })
  }

  function handleCerrarConfirm() {
    if (!filters) return
    cerrarMutation.mutate(
      { cohorte_id: filters.cohorte_id, mes: filters.mes, anio: filters.anio },
      {
        onSuccess: () => setShowCerrarDialog(false),
      },
    )
  }

  function handleExportar() {
    if (!filters) return
    exportarMutation.mutate(filters, {
      onSuccess: (blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `liquidaciones-${filters.anio}-${filters.mes}.csv`
        a.click()
        URL.revokeObjectURL(url)
      },
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Liquidaciones</h1>
        <Link
          to="/finanzas/grilla-salarial"
          className="text-sm text-blue-600 hover:underline"
        >
          Grilla salarial →
        </Link>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={[
                'pb-3 px-1 text-sm font-medium border-b-2 transition-colors',
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

      {activeTab === 'periodo' && (
        <div className="space-y-4">
          <FiltrosPeriodoForm onFilter={handleFilter} />

          {filters && (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleCalcular}
                disabled={calcularMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {calcularMutation.isPending ? 'Calculando...' : 'Calcular'}
              </button>
              {periodoData && (
                <>
                  <button
                    type="button"
                    onClick={handleExportar}
                    disabled={exportarMutation.isPending}
                    className="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200 disabled:opacity-50"
                  >
                    {exportarMutation.isPending ? 'Exportando...' : 'Exportar CSV'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCerrarDialog(true)}
                    className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700"
                  >
                    Cerrar liquidación
                  </button>
                </>
              )}
            </div>
          )}

          {isLoading && (
            <p className="text-sm text-gray-500 py-4">Cargando...</p>
          )}
          {error && (
            <p className="text-sm text-red-600 py-4">
              Error al cargar el período. Intentá de nuevo.
            </p>
          )}
          {periodoData && (
            <LiquidacionSegmentadaView data={periodoData} />
          )}
          {filters && !isLoading && !periodoData && !error && (
            <p className="text-sm text-gray-500 py-4">
              No hay liquidaciones para el período seleccionado. Calculá el período primero.
            </p>
          )}
        </div>
      )}

      {activeTab === 'historial' && <HistorialLiquidacionesView />}

      {showCerrarDialog && filters && periodoData && (
        <CerrarLiquidacionDialog
          filters={filters}
          periodoData={periodoData}
          onConfirm={handleCerrarConfirm}
          onCancel={() => setShowCerrarDialog(false)}
          isPending={cerrarMutation.isPending}
        />
      )}
    </div>
  )
}
