/**
 * VigenciasView.tsx — View to bulk-update vigencia for a team.
 *
 * Selector: materia × carrera × cohorte + new dates + mass confirmation.
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useUpdateVigencia } from '../hooks/useEquipos'

const vigenciaSchema = z
  .object({
    materia_id: z.string().uuid('Seleccioná una materia'),
    carrera_id: z.string().uuid('Seleccioná una carrera'),
    cohorte_id: z.string().uuid('Seleccioná un cohorte'),
    desde: z.string().min(1, 'La fecha de inicio es obligatoria'),
    hasta: z.string().optional().nullable(),
  })
  .refine(
    (d) => {
      if (!d.hasta) return true
      return d.hasta > d.desde
    },
    { message: 'La fecha de fin debe ser posterior a la de inicio', path: ['hasta'] },
  )

type VigenciaFormValues = z.infer<typeof vigenciaSchema>

export function VigenciasView() {
  const updateVigencia = useUpdateVigencia()
  const [resultado, setResultado] = useState<number | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<VigenciaFormValues>({ resolver: zodResolver(vigenciaSchema) })

  function onSubmit(values: VigenciaFormValues) {
    updateVigencia.mutate(
      {
        materia_id: values.materia_id,
        carrera_id: values.carrera_id,
        cohorte_id: values.cohorte_id,
        desde: values.desde,
        hasta: values.hasta ?? null,
      },
      {
        onSuccess: (data) => {
          setResultado(data.actualizadas)
          reset()
        },
      },
    )
  }

  return (
    <div className="space-y-4 max-w-lg">
      <p className="text-sm text-gray-600">
        Actualizá las fechas de vigencia de todas las asignaciones de un equipo.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {[
          { field: 'materia_id', label: 'Materia' },
          { field: 'carrera_id', label: 'Carrera' },
          { field: 'cohorte_id', label: 'Cohorte' },
        ].map(({ field, label }) => (
          <div key={field}>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <input
              {...register(field as keyof VigenciaFormValues)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              placeholder="UUID"
            />
            {errors[field as keyof VigenciaFormValues] && (
              <p className="text-red-600 text-xs mt-1">
                {errors[field as keyof VigenciaFormValues]?.message}
              </p>
            )}
          </div>
        ))}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nueva vigencia desde</label>
          <input
            {...register('desde')}
            type="date"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
          {errors.desde && (
            <p className="text-red-600 text-xs mt-1">{errors.desde.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nueva vigencia hasta (opcional)
          </label>
          <input
            {...register('hasta')}
            type="date"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
          {errors.hasta && (
            <p className="text-red-600 text-xs mt-1">{errors.hasta.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={updateVigencia.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {updateVigencia.isPending ? 'Actualizando...' : 'Actualizar vigencia masivamente'}
        </button>
      </form>

      {resultado !== null && (
        <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-800">
          Se actualizaron {resultado} asignación(es) correctamente.
        </div>
      )}
    </div>
  )
}
