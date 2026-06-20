/**
 * AvisosPage.tsx — Main page for managing avisos (COORDINADOR/ADMIN).
 *
 * Lists all avisos and provides a "Nuevo aviso" action.
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useAvisos } from '../hooks/useAvisos'
import { AvisosTable } from './AvisosTable'
import { AvisoForm } from './AvisoForm'

export function AvisosPage() {
  const [showForm, setShowForm] = useState(false)
  const { data: avisos = [], isLoading } = useAvisos()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Avisos</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Gestioná los avisos institucionales del tenant.
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-blue-700"
        >
          Nuevo aviso
        </button>
      </div>

      {showForm && (
        <div className="border border-gray-200 rounded p-4 bg-white">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-semibold text-gray-800">Nuevo aviso</h3>
            <button
              onClick={() => setShowForm(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
          <AvisoForm onSuccess={() => setShowForm(false)} onCancel={() => setShowForm(false)} />
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando avisos...</p>
      ) : (
        <AvisosTable avisos={avisos} />
      )}
    </div>
  )
}
