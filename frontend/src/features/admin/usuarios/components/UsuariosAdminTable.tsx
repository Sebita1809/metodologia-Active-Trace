/**
 * UsuariosAdminTable.tsx — Filterable table of admin users.
 *
 * Columns: nombre, identificación (DNI/CUIL), rol (modalidad_cobro), regional,
 *          estado, modalidad_cobro.
 * Actions inline: editar, toggle estado.
 */

import type { UsuarioAdmin, EstadoUsuario } from '../types'

interface UsuariosAdminTableProps {
  usuarios: UsuarioAdmin[]
  onEdit: (usuario: UsuarioAdmin) => void
  onToggleEstado: (usuario: UsuarioAdmin) => void
  isPendingToggle: boolean
}

function EstadoBadge({ estado }: { estado: EstadoUsuario }) {
  return (
    <span
      className={[
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
        estado === 'Activo'
          ? 'bg-green-100 text-green-700'
          : 'bg-gray-100 text-gray-500',
      ].join(' ')}
    >
      {estado}
    </span>
  )
}

export function UsuariosAdminTable({
  usuarios,
  onEdit,
  onToggleEstado,
  isPendingToggle,
}: UsuariosAdminTableProps) {
  if (usuarios.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-sm">No hay usuarios registrados.</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-md border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Nombre
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Email
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Roles
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Regional
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Modalidad cobro
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Estado
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Acciones
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {usuarios.map((u: UsuarioAdmin) => (
            <tr key={u.id}>
              <td className="px-4 py-2">
                <div className="font-medium text-gray-900">
                  {u.apellidos}, {u.nombre}
                </div>
                {u.legajo && (
                  <div className="text-xs text-gray-400">Leg. {u.legajo}</div>
                )}
              </td>
              <td className="px-4 py-2 text-gray-600 text-xs">{u.email}</td>
              <td className="px-4 py-2">
                <div className="flex flex-wrap gap-1">
                  {u.roles.length === 0 ? (
                    <span className="text-xs text-gray-400">—</span>
                  ) : (
                    u.roles.map((r, i) => (
                      <span
                        key={i}
                        className={[
                          'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                          r.vigencia === 'Vencida'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-blue-100 text-blue-700',
                        ].join(' ')}
                      >
                        {r.rol}
                      </span>
                    ))
                  )}
                </div>
              </td>
              <td className="px-4 py-2 text-gray-700">{u.regional ?? '—'}</td>
              <td className="px-4 py-2 text-gray-700">
                {u.modalidad_cobro ?? '—'}
              </td>
              <td className="px-4 py-2">
                <EstadoBadge estado={u.estado} />
              </td>
              <td className="px-4 py-2">
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => onEdit(u)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Editar
                  </button>
                  <button
                    type="button"
                    onClick={() => onToggleEstado(u)}
                    disabled={isPendingToggle}
                    className="text-xs text-gray-600 hover:underline disabled:opacity-50"
                  >
                    {u.estado === 'Activo' ? 'Desactivar' : 'Activar'}
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
