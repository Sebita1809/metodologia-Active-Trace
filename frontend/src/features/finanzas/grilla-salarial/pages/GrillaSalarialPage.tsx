/**
 * GrillaSalarialPage.tsx — Page for managing grilla salarial.
 *
 * Tabs: "Salario base" and "Plus".
 * <200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { SalariosBaseView } from '../components/SalariosBaseView'
import { PlusView } from '../components/PlusView'

type Tab = 'base' | 'plus'

const TABS: { id: Tab; label: string }[] = [
  { id: 'base', label: 'Salario base' },
  { id: 'plus', label: 'Plus' },
]

export function GrillaSalarialPage() {
  const [activeTab, setActiveTab] = useState<Tab>('base')

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-gray-900">Grilla salarial</h1>

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
        {activeTab === 'base' && <SalariosBaseView />}
        {activeTab === 'plus' && <PlusView />}
      </div>
    </div>
  )
}
