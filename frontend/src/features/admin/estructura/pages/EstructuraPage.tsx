/**
 * EstructuraPage.tsx — Main admin page for academic structure.
 *
 * Tabs: "Carreras", "Cohortes", "Materias".
 * <200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { CarrerasView } from '../components/CarrerasView'
import { CohorteView } from '../components/CohorteView'
import { MateriasView } from '../components/MateriasView'

type Tab = 'carreras' | 'cohortes' | 'materias'

const TABS: { id: Tab; label: string }[] = [
  { id: 'carreras', label: 'Carreras' },
  { id: 'cohortes', label: 'Cohortes' },
  { id: 'materias', label: 'Materias' },
]

export function EstructuraPage() {
  const [activeTab, setActiveTab] = useState<Tab>('carreras')

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-gray-900">Estructura académica</h1>

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
        {activeTab === 'carreras' && <CarrerasView />}
        {activeTab === 'cohortes' && <CohorteView />}
        {activeTab === 'materias' && <MateriasView />}
      </div>
    </div>
  )
}
