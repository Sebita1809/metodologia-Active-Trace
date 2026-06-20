/**
 * SalarioBaseForm.tsx — RHF+Zod form for creating/editing a salario base.
 *
 * Fields: rol (select), monto, desde, hasta.
 * Validates hasta > desde.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { SalarioBaseSchema, type SalarioBaseData } from '../types/schemas'
import type { SalarioBase } from '../types'

const ROL_OPTIONS = ['TUTOR', 'PROFESOR', 'COORDINADOR', 'NEXO', 'ADMIN']

interface SalarioBaseFormProps {
  initial?: SalarioBase
  onSubmit: (data: SalarioBaseData) => void
  onCancel: () => void
  isPending: boolean
}

export function SalarioBaseForm({
  initial,
  onSubmit,
  onCancel,
  isPending,
}: SalarioBaseFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SalarioBaseData>({
    resolver: zodResolver(SalarioBaseSchema),
    defaultValues: initial
      ? {
          rol: initial.rol,
          monto: initial.monto,
          desde: initial.desde,
          hasta: initial.hasta ?? undefined,
        }
      : { rol: '', monto: '', desde: '', hasta: undefined },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Rol <span className="text-red-500">*</span>
        </label>
        <select
          {...register('rol')}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Seleccionar rol...</option>
          {ROL_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        {errors.rol && (
          <p className="text-xs text-red-600">{errors.rol.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Monto <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          {...register('monto')}
          placeholder="ej: 50000.00"
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.monto && (
          <p className="text-xs text-red-600">{errors.monto.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Vigencia desde <span className="text-red-500">*</span>
        </label>
        <input
          type="date"
          {...register('desde')}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.desde && (
          <p className="text-xs text-red-600">{errors.desde.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Vigencia hasta (opcional)
        </label>
        <input
          type="date"
          {...register('hasta')}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.hasta && (
          <p className="text-xs text-red-600">{errors.hasta.message}</p>
        )}
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
          {isPending ? 'Guardando...' : initial ? 'Guardar cambios' : 'Crear salario base'}
        </button>
      </div>
    </form>
  )
}
