/**
 * ProgramasFechasPage.tsx — Admin page for programas and academic dates.
 *
 * Tabs: "Programas de materia" and "Fechas de evaluaciones".
 * Accessible to ADMIN and COORDINADOR (check router).
 * <200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { ProgramasView } from '../components/ProgramasView'
import { FechasAcademicasView } from '../components/FechasAcademicasView'

type Tab = 'programas' | 'fechas'

const TABS: { id: Tab; label: string }[] = [
  { id: 'programas', label: 'Programas de materia' },
  { id: 'fechas', label: 'Fechas de evaluaciones' },
]

export function ProgramasFechasPage() {
  const [activeTab, setActiveTab] = useState<Tab>('programas')

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-gray-900">Programas y fechas académicas</h1>

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
        {activeTab === 'programas' && <ProgramasView />}
        {activeTab === 'fechas' && <FechasAcademicasView />}
      </div>
    </div>
  )
}
