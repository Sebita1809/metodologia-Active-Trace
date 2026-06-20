/**
 * components/comunicacion/TrackingPanel.tsx — Real-time tracking of communication states.
 *
 * Polls GET /api/comunicaciones/?lote_id=... while messages are non-terminal.
 * Shows state badge per recipient. Stops polling when all are terminal.
 *
 * < 200 LOC, no `any`, no class components.
 */

import { useColaComunicaciones } from '../../hooks/useComunicaciones'
import type { EstadoComunicacion } from '../../types/comunicaciones'
import { isEstadoTerminal } from '../../types/comunicaciones'

interface TrackingPanelProps {
  loteId: string
}

function EstadoBadge({ estado }: { estado: EstadoComunicacion }) {
  const colorMap: Record<EstadoComunicacion, string> = {
    Pendiente: 'bg-yellow-100 text-yellow-800',
    Enviando: 'bg-blue-100 text-blue-800',
    Enviado: 'bg-green-100 text-green-800',
    Error: 'bg-red-100 text-red-800',
    Cancelado: 'bg-gray-100 text-gray-700',
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colorMap[estado]}`}
    >
      {estado}
    </span>
  )
}

export function TrackingPanel({ loteId }: TrackingPanelProps) {
  const { data: messages, isLoading } = useColaComunicaciones(loteId)

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando estado del lote...</p>
  }

  if (!messages || messages.length === 0) {
    return <p className="text-sm text-gray-500">Sin mensajes para mostrar.</p>
  }

  const allTerminal = messages.every((m) => isEstadoTerminal(m.estado))

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">
          Estado del lote ({messages.length} mensaje{messages.length !== 1 ? 's' : ''})
        </h3>
        {!allTerminal && (
          <span className="text-xs text-gray-500 animate-pulse">Actualizando...</span>
        )}
        {allTerminal && (
          <span className="text-xs text-green-600 font-medium">Completado</span>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">
                Destinatario
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">
                Enviado en
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {messages.map((msg) => (
              <tr key={msg.id}>
                <td className="px-4 py-2 text-gray-600">{msg.destinatario}</td>
                <td className="px-4 py-2">
                  <EstadoBadge estado={msg.estado} />
                </td>
                <td className="px-4 py-2 text-gray-500 text-xs">
                  {msg.enviado_at
                    ? new Date(msg.enviado_at).toLocaleString('es-AR')
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
