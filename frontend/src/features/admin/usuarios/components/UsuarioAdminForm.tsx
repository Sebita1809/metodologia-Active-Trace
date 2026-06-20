/**
 * UsuarioAdminForm.tsx — RHF+Zod form for creating/editing an admin user.
 *
 * SECURITY: CBU/alias go only in the body (never in URL params).
 * Fields: nombre, apellidos, email, dni, cuil, rol, regional, banco,
 *         cbu (validar 22 dígitos), alias, modalidad_cobro, facturador, estado.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { UsuarioAdminSchema, type UsuarioAdminData } from '../types/schemas'
import type { UsuarioAdmin } from '../types'

interface UsuarioAdminFormProps {
  initial?: UsuarioAdmin
  onSubmit: (data: UsuarioAdminData) => void
  onCancel: () => void
  isPending: boolean
}

export function UsuarioAdminForm({
  initial,
  onSubmit,
  onCancel,
  isPending,
}: UsuarioAdminFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<UsuarioAdminData>({
    resolver: zodResolver(UsuarioAdminSchema),
    defaultValues: initial
      ? {
          nombre: initial.nombre,
          apellidos: initial.apellidos,
          email: initial.email,
          dni: initial.dni ?? undefined,
          cuil: initial.cuil ?? undefined,
          cbu: initial.cbu ?? undefined,
          alias_cbu: initial.alias_cbu ?? undefined,
          banco: initial.banco ?? undefined,
          regional: initial.regional ?? undefined,
          legajo: initial.legajo ?? undefined,
          legajo_profesional: initial.legajo_profesional ?? undefined,
          sexo: initial.sexo ?? undefined,
          modalidad_cobro: initial.modalidad_cobro ?? undefined,
          facturador: initial.facturador,
          estado: initial.estado,
        }
      : {
          nombre: '',
          apellidos: '',
          email: '',
          dni: undefined,
          cuil: undefined,
          cbu: undefined,
          alias_cbu: undefined,
          banco: undefined,
          regional: undefined,
          legajo: undefined,
          legajo_profesional: undefined,
          sexo: undefined,
          modalidad_cobro: undefined,
          facturador: false,
          estado: 'Activo',
        },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Nombre <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            {...register('nombre')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.nombre && (
            <p className="text-xs text-red-600">{errors.nombre.message}</p>
          )}
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Apellidos <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            {...register('apellidos')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.apellidos && (
            <p className="text-xs text-red-600">{errors.apellidos.message}</p>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Email <span className="text-red-500">*</span>
        </label>
        <input
          type="email"
          {...register('email')}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.email && (
          <p className="text-xs text-red-600">{errors.email.message}</p>
        )}
      </div>

      {initial && initial.roles.length > 0 && (
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Roles</label>
          <div className="flex flex-wrap gap-1">
            {initial.roles.map((r, i) => (
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
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">DNI</label>
          <input
            type="text"
            {...register('dni')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">CUIL</label>
          <input
            type="text"
            {...register('cuil')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Regional</label>
          <input
            type="text"
            {...register('regional')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Banco</label>
          <input
            type="text"
            {...register('banco')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* CBU and alias — body only, never in URL */}
      <div className="bg-amber-50 border border-amber-100 rounded-md p-3 space-y-3">
        <p className="text-xs text-amber-700 font-medium">
          Datos bancarios — enviados de forma segura, nunca en URL.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-700">CBU (22 dígitos)</label>
            <input
              type="text"
              {...register('cbu')}
              maxLength={22}
              placeholder="22 dígitos"
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.cbu && (
              <p className="text-xs text-red-600">{errors.cbu.message}</p>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-700">Alias CBU</label>
            <input
              type="text"
              {...register('alias_cbu')}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Modalidad de cobro</label>
          <select
            {...register('modalidad_cobro')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Sin definir</option>
            <option value="Factura">Factura</option>
            <option value="Liquidacion">Liquidación</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Estado</label>
          <select
            {...register('estado')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="Activo">Activo</option>
            <option value="Inactivo">Inactivo</option>
          </select>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="facturador"
          {...register('facturador')}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <label htmlFor="facturador" className="text-sm text-gray-700">
          Es facturador
        </label>
      </div>

      <div className="flex gap-3 justify-end pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {isPending ? 'Guardando...' : initial ? 'Guardar cambios' : 'Crear usuario'}
        </button>
      </div>
    </form>
  )
}
