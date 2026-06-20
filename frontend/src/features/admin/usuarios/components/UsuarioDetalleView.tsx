/**
 * UsuarioDetalleView.tsx — Read-only detail view of a user.
 *
 * Shows all user data including CBU/alias as returned by the API.
 * CBU/alias displayed as plain text (backend decrypts before responding).
 * This view is read-only — no editing.
 */

import type { UsuarioAdmin } from '../types'

interface UsuarioDetalleViewProps {
  usuario: UsuarioAdmin
  onClose: () => void
}

function Field({ label, value }: { label: string; value: string | null | boolean | undefined }) {
  const display =
    value === null || value === undefined || value === ''
      ? '—'
      : typeof value === 'boolean'
      ? value ? 'Sí' : 'No'
      : String(value)

  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">
        {label}
      </dt>
      <dd className="text-sm text-gray-900">{display}</dd>
    </div>
  )
}

export function UsuarioDetalleView({ usuario, onClose }: UsuarioDetalleViewProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {usuario.apellidos}, {usuario.nombre}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        <dl className="grid grid-cols-2 gap-4">
          <Field label="Email" value={usuario.email} />
          <Field label="Estado" value={usuario.estado} />
          <div className="flex flex-col gap-0.5 col-span-2">
            <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Roles
            </dt>
            <dd className="text-sm text-gray-900">
              {usuario.roles.length === 0 ? (
                '—'
              ) : (
                <div className="flex flex-wrap gap-1 mt-1">
                  {usuario.roles.map((r, i) => (
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
                      {r.materia && (
                        <span className="ml-1 opacity-70">({r.materia})</span>
                      )}
                    </span>
                  ))}
                </div>
              )}
            </dd>
          </div>
          <Field label="DNI" value={usuario.dni} />
          <Field label="CUIL" value={usuario.cuil} />
          <Field label="Regional" value={usuario.regional} />
          <Field label="Banco" value={usuario.banco} />
          <Field label="Legajo" value={usuario.legajo} />
          <Field label="Legajo profesional" value={usuario.legajo_profesional} />
          <Field label="Modalidad de cobro" value={usuario.modalidad_cobro} />
          <Field label="Facturador" value={usuario.facturador} />
          <Field label="CBU" value={usuario.cbu} />
          <Field label="Alias CBU" value={usuario.alias_cbu} />
          <Field label="Sexo" value={usuario.sexo} />
          <Field label="Creado" value={new Date(usuario.created_at).toLocaleDateString('es-AR')} />
        </dl>

        <div className="flex justify-end mt-6">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  )
}
