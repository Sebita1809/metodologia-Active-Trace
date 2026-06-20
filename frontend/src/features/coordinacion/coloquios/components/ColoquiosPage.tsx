/**
 * ColoquiosPage.tsx — Main page for coloquios management.
 *
 * Header: 4 KPI cards (useMetricasColoquios).
 * Tabs: "Convocatorias", "Agenda de reservas", "Registro académico".
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useMetricasColoquios } from '../hooks/useColoquios'
import { ConvocatoriasView } from './ConvocatoriasView'
import { AgendaReservasView } from './AgendaReservasView'
import { RegistroAcademicoView } from './RegistroAcademicoView'

type Tab = 'convocatorias' | 'agenda' | 'registro'

interface KpiCardProps {
  label: string
  value: number | undefined
}

function KpiCard({ label, value }: KpiCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
      <p className="text-2xl font-bold text-blue-600">{value ?? '—'}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  )
}

export function ColoquiosPage() {
  const [activeTab, setActiveTab] = useState<Tab>('convocatorias')
  const { data: metricas } = useMetricasColoquios()

  return (
    <div className="space-y-4">
      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard label="Alumnos cargados" value={metricas?.total_alumnos_cargados} />
        <KpiCard label="Instancias activas" value={metricas?.instancias_activas} />
        <KpiCard label="Reservas activas" value={metricas?.reservas_activas} />
        <KpiCard label="Notas registradas" value={metricas?.notas_registradas} />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          {([
            { id: 'convocatorias', label: 'Convocatorias' },
            { id: 'agenda', label: 'Agenda de reservas' },
            { id: 'registro', label: 'Registro académico' },
          ] as { id: Tab; label: string }[]).map((tab) => (
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

      {activeTab === 'convocatorias' && <ConvocatoriasView />}
      {activeTab === 'agenda' && <AgendaReservasView />}
      {activeTab === 'registro' && <RegistroAcademicoView />}
    </div>
  )
}
