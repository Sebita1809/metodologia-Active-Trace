/**
 * EquiposPage.tsx — Main page for managing equipo docente.
 *
 * Tabs: "Asignaciones", "Alta masiva", "Clonar equipo", "Vigencias".
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { AsignacionesView } from '../components/AsignacionesView'
import { AsignacionMasivaForm } from '../components/AsignacionMasivaForm'
import { ClonarEquipoForm } from '../components/ClonarEquipoForm'
import { VigenciasView } from '../components/VigenciasView'

type Tab = 'asignaciones' | 'masiva' | 'clonar' | 'vigencias'

const TABS: { id: Tab; label: string }[] = [
  { id: 'asignaciones', label: 'Asignaciones' },
  { id: 'masiva', label: 'Alta masiva' },
  { id: 'clonar', label: 'Clonar equipo' },
  { id: 'vigencias', label: 'Vigencias' },
]

export function EquiposPage() {
  const [activeTab, setActiveTab] = useState<Tab>('asignaciones')

  return (
    <div className="space-y-4">
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

      <div>
        {activeTab === 'asignaciones' && <AsignacionesView />}
        {activeTab === 'masiva' && <AsignacionMasivaForm />}
        {activeTab === 'clonar' && <ClonarEquipoForm />}
        {activeTab === 'vigencias' && <VigenciasView />}
      </div>
    </div>
  )
}
