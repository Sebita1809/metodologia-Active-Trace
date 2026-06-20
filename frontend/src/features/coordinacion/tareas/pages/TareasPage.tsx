/**
 * TareasPage.tsx — Main page for tareas internas.
 *
 * Bifurcation by role:
 *   - TUTOR/PROFESOR → MisTareasView only
 *   - COORDINADOR/ADMIN → tabs "Mis tareas" + "Todas las tareas"
 *
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useAuth } from '@/features/auth/context/AuthContext'
import { MisTareasView } from '../components/MisTareasView'
import { TareasGlobalView } from '../components/TareasGlobalView'
import { CrearTareaForm } from '../components/CrearTareaForm'

type TabCoord = 'mis-tareas' | 'todas'

export function TareasPage() {
  const { claims } = useAuth()
  const [activeTab, setActiveTab] = useState<TabCoord>('mis-tareas')
  const [showForm, setShowForm] = useState(false)

  const roles = claims?.roles ?? []
  const isCoord = roles.includes('COORDINADOR') || roles.includes('ADMIN')

  if (!isCoord) {
    // TUTOR or PROFESOR — only see their own tasks
    return (
      <div className="space-y-4">
        <h1 className="text-lg font-semibold text-gray-900">Mis tareas</h1>
        <MisTareasView />
      </div>
    )
  }

  // COORDINADOR / ADMIN — two-tab view + create form
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-900">Tareas internas</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-blue-700"
        >
          Nueva tarea
        </button>
      </div>

      {showForm && (
        <div className="border border-gray-200 rounded p-4 bg-white">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-semibold text-gray-800">Nueva tarea</h3>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">
              ✕
            </button>
          </div>
          <CrearTareaForm onSuccess={() => setShowForm(false)} onCancel={() => setShowForm(false)} />
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          {([
            { id: 'mis-tareas', label: 'Mis tareas' },
            { id: 'todas', label: 'Todas las tareas' },
          ] as { id: TabCoord; label: string }[]).map((tab) => (
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

      {activeTab === 'mis-tareas' && <MisTareasView />}
      {activeTab === 'todas' && <TareasGlobalView />}
    </div>
  )
}
