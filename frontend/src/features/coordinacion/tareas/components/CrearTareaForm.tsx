/**
 * CrearTareaForm.tsx — Form to create a task and assign it to a docente (RHF + Zod).
 *
 * Visible only for COORDINADOR/ADMIN (caller responsibility).
 * < 200 LOC, no `any`, no class components.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { tareaFormSchema, type TareaFormValues } from '../../schemas'
import { useCreateTarea } from '../hooks/useTareas'

interface CrearTareaFormProps {
  onSuccess?: () => void
  onCancel?: () => void
}

export function CrearTareaForm({ onSuccess, onCancel }: CrearTareaFormProps) {
  const createTarea = useCreateTarea()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TareaFormValues>({ resolver: zodResolver(tareaFormSchema) })

  function onSubmit(values: TareaFormValues) {
    createTarea.mutate(
      {
        titulo: values.titulo,
        descripcion: values.descripcion,
        criterio_cierre: values.criterio_cierre ?? null,
        materia_id: values.materia_id ?? null,
        asignada_a: values.asignada_a,
      },
      {
        onSuccess: () => {
          reset()
          onSuccess?.()
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-lg">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Título</label>
        <input
          {...register('titulo')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {errors.titulo && <p className="text-red-600 text-xs mt-1">{errors.titulo.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
        <textarea
          {...register('descripcion')}
          rows={3}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {errors.descripcion && (
          <p className="text-red-600 text-xs mt-1">{errors.descripcion.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Criterio de cierre (opcional)
        </label>
        <input
          {...register('criterio_cierre')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="Ej: Adjuntar captura de pantalla"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Materia (UUID, opcional)
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
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Docente asignado (UUID)
        </label>
        <input
          {...register('asignada_a')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="UUID del docente"
        />
        {errors.asignada_a && (
          <p className="text-red-600 text-xs mt-1">{errors.asignada_a.message}</p>
        )}
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={createTarea.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {createTarea.isPending ? 'Creando...' : 'Crear tarea'}
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
