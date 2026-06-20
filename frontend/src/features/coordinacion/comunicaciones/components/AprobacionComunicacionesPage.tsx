/**
 * AprobacionComunicacionesPage.tsx — Approval queue for pending communications.
 *
 * Lists pending lotes with: docente emisor, materia, destinatarios, fecha.
 * Actions: "Aprobar" (inline/confirm) and "Cancelar" (confirm dialog).
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useAprobarLote, useCancelarLote, useLotesPendientes } from '../hooks/useAprobacion'
import type { ComunicacionRead } from '../types'

// Group ComunicacionRead by lote_id to build the approval queue view
function groupByLote(items: ComunicacionRead[]) {
  return Object.values(
    items.reduce<Record<string, { lote_id: string; enviado_por: string; materia_id: string; cantidad: number; created_at: string }>>(
      (acc, item) => {
        if (!acc[item.lote_id]) {
          acc[item.lote_id] = {
            lote_id: item.lote_id,
            enviado_por: item.enviado_por,
            materia_id: item.materia_id,
            cantidad: 0,
            created_at: item.created_at,
          }
        }
        acc[item.lote_id].cantidad += 1
        return acc
      },
      {},
    ),
  )
}

export function AprobacionComunicacionesPage() {
  const { data: items = [], isLoading } = useLotesPendientes()
  const aprobarLote = useAprobarLote()
  const cancelarLote = useCancelarLote()
  const [cancelandoLoteId, setCancelandoLoteId] = useState<string | null>(null)
  const [aprobandoLoteId, setAprobandoLoteId] = useState<string | null>(null)

  const lotes = groupByLote(items)

  function handleAprobar(lote_id: string) {
    setAprobandoLoteId(lote_id)
    aprobarLote.mutate(lote_id, {
      onSettled: () => setAprobandoLoteId(null),
    })
  }

  function handleCancelar(lote_id: string) {
    cancelarLote.mutate(lote_id, {
      onSuccess: () => setCancelandoLoteId(null),
    })
  }

  const cancelandoLote = lotes.find((l) => l.lote_id === cancelandoLoteId)

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-gray-900">Aprobación de comunicaciones</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Revisá y aprobá o cancelá los lotes de comunicaciones pendientes.
        </p>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando lotes pendientes...</p>
      ) : lotes.length === 0 ? (
        <div className="text-center py-8 text-sm text-gray-500">
          Sin comunicaciones pendientes de aprobación.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Docente emisor</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Materia</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">Destinatarios</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Fecha</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {lotes.map((lote) => (
                <tr key={lote.lote_id}>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{lote.enviado_por}</td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{lote.materia_id}</td>
                  <td className="px-4 py-2 text-right text-gray-700">{lote.cantidad}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">
                    {new Date(lote.created_at).toLocaleDateString('es-AR')}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleAprobar(lote.lote_id)}
                        disabled={aprobarLote.isPending && aprobandoLoteId === lote.lote_id}
                        className="text-green-700 hover:underline text-xs disabled:opacity-50"
                      >
                        {aprobarLote.isPending && aprobandoLoteId === lote.lote_id
                          ? 'Aprobando...'
                          : 'Aprobar'}
                      </button>
                      <button
                        onClick={() => setCancelandoLoteId(lote.lote_id)}
                        className="text-red-600 hover:underline text-xs"
                      >
                        Cancelar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Cancel confirmation dialog */}
      {cancelandoLoteId && cancelandoLote && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full mx-4 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Confirmar cancelación</h3>
            <p className="text-sm text-gray-600">
              ¿Confirmás la cancelación de{' '}
              <strong>{cancelandoLote.cantidad} mensaje(s)</strong> de este lote?
              Esta acción no se puede deshacer.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => handleCancelar(cancelandoLoteId)}
                disabled={cancelarLote.isPending}
                className="bg-red-600 text-white px-4 py-2 rounded text-sm hover:bg-red-700 disabled:opacity-50"
              >
                {cancelarLote.isPending ? 'Cancelando...' : 'Confirmar cancelación'}
              </button>
              <button
                onClick={() => setCancelandoLoteId(null)}
                className="bg-gray-100 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-200"
              >
                Mantener pendiente
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
