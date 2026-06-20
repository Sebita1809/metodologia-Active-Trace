/**
 * MateriaForm.tsx — RHF+Zod form for creating/editing a materia.
 *
 * Fields: nombre (required), código (optional), estado (toggle activo/inactivo).
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { MateriaSchema, type MateriaData } from '../types/schemas'
import type { Materia } from '../types'

interface MateriaFormProps {
  initial?: Materia
  onSubmit: (data: MateriaData) => void
  onCancel: () => void
  isPending: boolean
}

export function MateriaForm({ initial, onSubmit, onCancel, isPending }: MateriaFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<MateriaData>({
    resolver: zodResolver(MateriaSchema),
    defaultValues: initial
      ? {
          nombre: initial.nombre,
          codigo: initial.codigo ?? undefined,
          estado: initial.estado,
        }
      : { nombre: '', codigo: undefined, estado: 'Activa' },
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
            placeholder="ej: Análisis Matemático I"
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.nombre && (
            <p className="text-xs text-red-600">{errors.nombre.message}</p>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Código (opcional)
          </label>
          <input
            type="text"
            {...register('codigo')}
            placeholder="ej: MAT-101"
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
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
          {isPending ? 'Guardando...' : initial ? 'Guardar cambios' : 'Crear materia'}
        </button>
      </div>
    </form>
  )
}
