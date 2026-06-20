/**
 * AuditoriaPage.tsx — Main page for auditoría.
 *
 * Tabs:
 *   - "Panel" — visible to COORDINADOR and ADMIN
 *   - "Log completo" — visible to ADMIN only (hidden tab for COORDINADOR)
 *
 * Uses RequireRole inline for the log completo tab content.
 * <200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { AuditoriaPanelView } from '../components/AuditoriaPanelView'
import { LogCompletoView } from '../components/LogCompletoView'
import { RequireRole } from '@/shared/components/RequireRole'
import { useAuth } from '@/features/auth/context/AuthContext'

type Tab = 'panel' | 'log'

export function AuditoriaPage() {
  const { claims } = useAuth()
  const [activeTab, setActiveTab] = useState<Tab>('panel')

  const isAdmin = claims?.roles.includes('ADMIN') ?? false

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-gray-900">Auditoría</h1>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          <button
            onClick={() => setActiveTab('panel')}
            className={[
              'pb-3 px-1 text-sm font-medium border-b-2 transition-colors',
              activeTab === 'panel'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            ].join(' ')}
          >
            Panel
          </button>
          {/* Log completo tab only shown for ADMIN */}
          {isAdmin && (
            <button
              onClick={() => setActiveTab('log')}
              className={[
                'pb-3 px-1 text-sm font-medium border-b-2 transition-colors',
                activeTab === 'log'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              ].join(' ')}
            >
              Log completo
            </button>
          )}
        </nav>
      </div>

      <div>
        {activeTab === 'panel' && <AuditoriaPanelView />}
        {activeTab === 'log' && (
          <RequireRole roles={['ADMIN']}>
            <LogCompletoView />
          </RequireRole>
        )}
      </div>
    </div>
  )
}
