/**
 * AvisosTable.tsx — Table of avisos with inline actions.
 *
 * Columns: título, severidad, alcance, estado, fecha inicio, fecha fin, acks.
 * Actions: editar, toggle activo, eliminar.
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useDeleteAviso, useUpdateAviso } from '../hooks/useAvisos'
import { AvisoForm } from './AvisoForm'
import { AckPanel } from './AckPanel'
import { ConfirmDeleteDialog } from './ConfirmDeleteDialog'
import type { Aviso } from '../types'

const SEVERIDAD_BADGE: Record<string, string> = {
  info: 'bg-blue-50 text-blue-700',
  advertencia: 'bg-yellow-50 text-yellow-700',
  critica: 'bg-red-50 text-red-700',
}

interface AvisosTableProps {
  avisos: Aviso[]
}

export function AvisosTable({ avisos }: AvisosTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [ackPanelId, setAckPanelId] = useState<string | null>(null)
  const updateAviso = useUpdateAviso()
  const deleteAviso = useDeleteAviso()

  if (avisos.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-gray-500">
        No hay avisos creados. Creá el primero con el botón "Nuevo aviso".
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Título</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Severidad</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Alcance</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Inicio</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Fin</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Acks</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {avisos.map((aviso) => (
              <tr key={aviso.id}>
                <td className="px-4 py-2 font-medium text-gray-800">{aviso.titulo}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${SEVERIDAD_BADGE[aviso.severidad] ?? ''}`}>
                    {aviso.severidad}
                  </span>
                </td>
                <td className="px-4 py-2 text-gray-600 capitalize">{aviso.alcance}</td>
                <td className="px-4 py-2">
                  <span className={aviso.activo ? 'text-green-700' : 'text-gray-400'}>
                    {aviso.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td className="px-4 py-2 text-gray-600">{aviso.fecha_inicio}</td>
                <td className="px-4 py-2 text-gray-600">{aviso.fecha_fin ?? '—'}</td>
                <td className="px-4 py-2 text-right">
                  {aviso.require_ack ? (
                    <button
                      onClick={() => setAckPanelId(ackPanelId === aviso.id ? null : aviso.id)}
                      className="text-blue-600 hover:underline text-xs"
                    >
                      {aviso.total_acks} acks
                    </button>
                  ) : (
                    <span className="text-gray-400 text-xs">—</span>
                  )}
                </td>
                <td className="px-4 py-2 text-right">
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => setEditingId(editingId === aviso.id ? null : aviso.id)}
                      className="text-gray-500 hover:text-blue-600 text-xs"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() =>
                        updateAviso.mutate({ id: aviso.id, body: { activo: !aviso.activo } })
                      }
                      className="text-gray-500 hover:text-yellow-600 text-xs"
                    >
                      {aviso.activo ? 'Desactivar' : 'Activar'}
                    </button>
                    <button
                      onClick={() => setDeletingId(aviso.id)}
                      className="text-gray-500 hover:text-red-600 text-xs"
                    >
                      Eliminar
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editingId && (
        <div className="border border-gray-200 rounded p-4 bg-white">
          <AvisoForm
            aviso={avisos.find((a) => a.id === editingId)}
            onSuccess={() => setEditingId(null)}
            onCancel={() => setEditingId(null)}
          />
        </div>
      )}

      {ackPanelId && (
        <div className="border border-gray-200 rounded p-4 bg-white">
          <AckPanel aviso={avisos.find((a) => a.id === ackPanelId)!} />
        </div>
      )}

      {deletingId && (
        <ConfirmDeleteDialog
          title="Eliminar aviso"
          message="¿Confirmás la eliminación de este aviso? Los destinatarios dejarán de verlo."
          onConfirm={() =>
            deleteAviso.mutate(deletingId, { onSuccess: () => setDeletingId(null) })
          }
          onCancel={() => setDeletingId(null)}
          isLoading={deleteAviso.isPending}
        />
      )}
    </div>
  )
}
