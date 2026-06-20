/**
 * EncuentrosAdminPage.tsx — Admin page for encuentros and guardias.
 *
 * Tabs: "Encuentros del tenant", "Guardias".
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { EncuentrosTenantView } from './EncuentrosTenantView'
import { GuardiasView } from './GuardiasView'

type Tab = 'encuentros' | 'guardias'

export function EncuentrosAdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>('encuentros')

  return (
    <div className="space-y-4">
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          {([
            { id: 'encuentros', label: 'Encuentros del tenant' },
            { id: 'guardias', label: 'Guardias' },
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

      {activeTab === 'encuentros' && <EncuentrosTenantView />}
      {activeTab === 'guardias' && <GuardiasView />}
    </div>
  )
}
