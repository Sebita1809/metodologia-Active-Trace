/**
 * FechaAcademicaForm.tsx — RHF+Zod form for creating/editing a fecha académica.
 *
 * Fields: materia (select), tipo (parcial/TP/coloquio), número de instancia, fecha, cohorte, título.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { FechaAcademicaSchema, type FechaAcademicaData } from '../types/schemas'
import { useCohortes, useMaterias } from '@/features/admin/estructura/hooks/useEstructura'
import type { FechaAcademica } from '../types'

interface FechaAcademicaFormProps {
  initial?: FechaAcademica
  onSubmit: (data: FechaAcademicaData) => void
  onCancel: () => void
  isPending: boolean
}

export function FechaAcademicaForm({
  initial,
  onSubmit,
  onCancel,
  isPending,
}: FechaAcademicaFormProps) {
  const { data: materias, isLoading: loadingMaterias } = useMaterias()
  const { data: cohortes, isLoading: loadingCohortes } = useCohortes()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FechaAcademicaData>({
    resolver: zodResolver(FechaAcademicaSchema),
    defaultValues: initial
      ? {
          materia_id: initial.materia_id,
          cohorte_id: initial.cohorte_id,
          tipo: initial.tipo,
          numero: initial.numero,
          fecha: initial.fecha,
          titulo: initial.titulo,
          periodo: initial.periodo ?? undefined,
        }
      : {
          materia_id: '',
          cohorte_id: '',
          tipo: 'parcial',
          numero: 1,
          fecha: '',
          titulo: '',
          periodo: undefined,
        },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Materia <span className="text-red-500">*</span>
          </label>
          <select
            {...register('materia_id')}
            disabled={loadingMaterias}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Seleccionar materia...</option>
            {materias?.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}
              </option>
            ))}
          </select>
          {errors.materia_id && (
            <p className="text-xs text-red-600">{errors.materia_id.message}</p>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Cohorte <span className="text-red-500">*</span>
          </label>
          <select
            {...register('cohorte_id')}
            disabled={loadingCohortes}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Seleccionar cohorte...</option>
            {cohortes?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
          {errors.cohorte_id && (
            <p className="text-xs text-red-600">{errors.cohorte_id.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Tipo <span className="text-red-500">*</span>
          </label>
          <select
            {...register('tipo')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="parcial">Parcial</option>
            <option value="TP">Trabajo Práctico</option>
            <option value="coloquio">Coloquio</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            N° instancia <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            {...register('numero', { valueAsNumber: true })}
            min={1}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.numero && (
            <p className="text-xs text-red-600">{errors.numero.message}</p>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Fecha <span className="text-red-500">*</span>
        </label>
        <input
          type="date"
          {...register('fecha')}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
        />
        {errors.fecha && (
          <p className="text-xs text-red-600">{errors.fecha.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Título descriptivo <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          {...register('titulo')}
          placeholder="ej: 1er Parcial — Unidades 1-3"
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.titulo && (
          <p className="text-xs text-red-600">{errors.titulo.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">Período (opcional)</label>
        <input
          type="text"
          {...register('periodo')}
          placeholder="ej: 1er cuatrimestre 2025"
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
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
          {isPending ? 'Guardando...' : initial ? 'Guardar cambios' : 'Crear fecha'}
        </button>
      </div>
    </form>
  )
}
