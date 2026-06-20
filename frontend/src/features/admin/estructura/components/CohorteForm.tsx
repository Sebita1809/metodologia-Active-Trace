/**
 * CohorteForm.tsx — RHF+Zod form for creating/editing a cohorte.
 *
 * Fields: carrera (select), nombre, año, vig_desde, vig_hasta, estado.
 * Validates vig_hasta > vig_desde.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { CohorteSchema, type CohorteData } from '../types/schemas'
import { useCarreras } from '../hooks/useEstructura'
import type { Cohorte } from '../types'

interface CohorteFormProps {
  initial?: Cohorte
  onSubmit: (data: CohorteData) => void
  onCancel: () => void
  isPending: boolean
}

export function CohorteForm({ initial, onSubmit, onCancel, isPending }: CohorteFormProps) {
  const { data: carreras, isLoading: loadingCarreras } = useCarreras()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CohorteData>({
    resolver: zodResolver(CohorteSchema),
    defaultValues: initial
      ? {
          carrera_id: initial.carrera_id,
          nombre: initial.nombre,
          anio: initial.anio,
          vig_desde: initial.vig_desde,
          vig_hasta: initial.vig_hasta ?? undefined,
          estado: initial.estado,
        }
      : {
          carrera_id: '',
          nombre: '',
          anio: new Date().getFullYear(),
          vig_desde: '',
          vig_hasta: undefined,
          estado: 'Activa',
        },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Carrera <span className="text-red-500">*</span>
        </label>
        <select
          {...register('carrera_id')}
          disabled={loadingCarreras}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Seleccionar carrera...</option>
          {carreras?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.codigo} — {c.nombre}
            </option>
          ))}
        </select>
        {errors.carrera_id && (
          <p className="text-xs text-red-600">{errors.carrera_id.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Nombre <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            {...register('nombre')}
            placeholder="ej: Cohorte 2024"
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.nombre && (
            <p className="text-xs text-red-600">{errors.nombre.message}</p>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Año inicio <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            {...register('anio', { valueAsNumber: true })}
            min={2000}
            max={new Date().getFullYear() + 5}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.anio && (
            <p className="text-xs text-red-600">{errors.anio.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Vigencia desde <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            {...register('vig_desde')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.vig_desde && (
            <p className="text-xs text-red-600">{errors.vig_desde.message}</p>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Vigencia hasta (opcional)
          </label>
          <input
            type="date"
            {...register('vig_hasta')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.vig_hasta && (
            <p className="text-xs text-red-600">{errors.vig_hasta.message}</p>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">Estado</label>
        <select
          {...register('estado')}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-40"
        >
          <option value="Activa">Activa</option>
          <option value="Inactiva">Inactiva</option>
        </select>
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
          {isPending ? 'Guardando...' : initial ? 'Guardar cambios' : 'Crear cohorte'}
        </button>
      </div>
    </form>
  )
}
