/**
 * AckPanel.tsx — Detail panel showing acknowledgment count for an aviso.
 *
 * Shows acks received vs. total recipients for avisos with require_ack=true.
 * < 200 LOC, no `any`, no class components.
 */

import { useAckCount } from '../hooks/useAvisos'
import type { Aviso } from '../types'

interface AckPanelProps {
  aviso: Aviso
  totalDestinatarios?: number
}

export function AckPanel({ aviso, totalDestinatarios }: AckPanelProps) {
  const { data: ackCount, isLoading } = useAckCount(aviso.id)

  if (!aviso.require_ack) {
    return (
      <p className="text-sm text-gray-500">Este aviso no requiere confirmación de lectura.</p>
    )
  }

  const total = totalDestinatarios ?? 0
  const acks = ackCount ?? aviso.total_acks

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-gray-800">Confirmaciones de lectura</h4>

      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando...</p>
      ) : (
        <div className="flex items-center gap-4">
          <div className="text-center">
            <span className="block text-2xl font-bold text-blue-600">{acks}</span>
            <span className="text-xs text-gray-500">recibidos</span>
          </div>
          {total > 0 && (
            <>
              <span className="text-gray-300 text-lg">/</span>
              <div className="text-center">
                <span className="block text-2xl font-bold text-gray-700">{total}</span>
                <span className="text-xs text-gray-500">total destinatarios</span>
              </div>
              <div className="flex-1">
                <div className="h-2 bg-gray-200 rounded-full">
                  <div
                    className="h-2 bg-blue-500 rounded-full"
                    style={{ width: `${Math.min((acks / total) * 100, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {total > 0 ? Math.round((acks / total) * 100) : 0}% confirmado
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
