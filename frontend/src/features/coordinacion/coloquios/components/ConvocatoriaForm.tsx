/**
 * ConvocatoriaForm.tsx — Form to create a convocatoria (RHF + Zod).
 *
 * Fields: materia, instancia, array of días (dynamic: add/remove days with cupos).
 * Validates: cupos > 0 per day.
 * < 200 LOC, no `any`, no class components.
 */

import { useFieldArray, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { convocatoriaFormSchema, type ConvocatoriaFormValues } from '../../schemas'
import { useCreateEvaluacion } from '../hooks/useColoquios'

interface ConvocatoriaFormProps {
  onSuccess?: () => void
  onCancel?: () => void
}

export function ConvocatoriaForm({ onSuccess, onCancel }: ConvocatoriaFormProps) {
  const createEvaluacion = useCreateEvaluacion()
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ConvocatoriaFormValues>({
    resolver: zodResolver(convocatoriaFormSchema),
    defaultValues: { dias_disponibles: [{ fecha: '', cupos: 10 }] },
  })

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'dias_disponibles',
  })

  function onSubmit(values: ConvocatoriaFormValues) {
    createEvaluacion.mutate(values, {
      onSuccess: () => {
        reset()
        onSuccess?.()
      },
    })
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-lg">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Materia (UUID)
        </label>
        <input
          {...register('materia_id')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="UUID"
        />
        {errors.materia_id && (
          <p className="text-red-600 text-xs mt-1">{errors.materia_id.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Instancia</label>
        <input
          {...register('instancia', { valueAsNumber: true })}
          type="number"
          min={1}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {errors.instancia && (
          <p className="text-red-600 text-xs mt-1">{errors.instancia.message}</p>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">Días disponibles</label>
          <button
            type="button"
            onClick={() => append({ fecha: '', cupos: 10 })}
            className="text-blue-600 text-xs hover:underline"
          >
            + Agregar día
          </button>
        </div>
        {fields.map((field, idx) => (
          <div key={field.id} className="flex gap-3 items-start mb-2">
            <div className="flex-1">
              <input
                {...register(`dias_disponibles.${idx}.fecha`)}
                type="date"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              />
              {errors.dias_disponibles?.[idx]?.fecha && (
                <p className="text-red-600 text-xs mt-1">
                  {errors.dias_disponibles[idx].fecha?.message}
                </p>
              )}
            </div>
            <div className="w-28">
              <input
                {...register(`dias_disponibles.${idx}.cupos`, { valueAsNumber: true })}
                type="number"
                min={1}
                placeholder="Cupos"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              />
              {errors.dias_disponibles?.[idx]?.cupos && (
                <p className="text-red-600 text-xs mt-1">
                  {errors.dias_disponibles[idx].cupos?.message}
                </p>
              )}
            </div>
            {fields.length > 1 && (
              <button
                type="button"
                onClick={() => remove(idx)}
                className="text-red-400 hover:text-red-600 mt-2"
              >
                ✕
              </button>
            )}
          </div>
        ))}
        {errors.dias_disponibles && !Array.isArray(errors.dias_disponibles) && (
          <p className="text-red-600 text-xs mt-1">{errors.dias_disponibles.message}</p>
        )}
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={createEvaluacion.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {createEvaluacion.isPending ? 'Creando...' : 'Crear convocatoria'}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-200"
          >
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}
