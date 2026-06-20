/**
 * GuardiaForm.tsx — Form to register a guardia (RHF + Zod).
 *
 * Fields: quién cubrió, materia, carrera/cohorte, día, horario (time), estado, comentarios.
 * Validates: horario is required.
 * < 200 LOC, no `any`, no class components.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { guardiaFormSchema, type GuardiaFormValues } from '../../schemas'
import { useCreateGuardia } from '../hooks/useEncuentros'

interface GuardiaFormProps {
  asignacionId: string
  onSuccess?: () => void
  onCancel?: () => void
}

export function GuardiaForm({ asignacionId, onSuccess, onCancel }: GuardiaFormProps) {
  const createGuardia = useCreateGuardia()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<GuardiaFormValues>({
    resolver: zodResolver(guardiaFormSchema),
    defaultValues: { asignacion_id: asignacionId, estado: 'Registrada' },
  })

  function onSubmit(values: GuardiaFormValues) {
    createGuardia.mutate(
      {
        asignacion_id: values.asignacion_id,
        cubierto_por: values.cubierto_por,
        materia_id: values.materia_id ?? null,
        carrera_id: values.carrera_id ?? null,
        cohorte_id: values.cohorte_id ?? null,
        dia: values.dia,
        horario: values.horario,
        estado: values.estado,
        comentarios: values.comentarios ?? null,
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
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Quién cubrió (UUID docente)
        </label>
        <input
          {...register('cubierto_por')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="UUID"
        />
        {errors.cubierto_por && (
          <p className="text-red-600 text-xs mt-1">{errors.cubierto_por.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Día</label>
          <input
            {...register('dia')}
            type="date"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
          {errors.dia && <p className="text-red-600 text-xs mt-1">{errors.dia.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Horario</label>
          <input
            {...register('horario')}
            type="time"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
          {errors.horario && (
            <p className="text-red-600 text-xs mt-1">{errors.horario.message}</p>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
        <select
          {...register('estado')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        >
          <option value="Registrada">Registrada</option>
          <option value="Auditada">Auditada</option>
          <option value="Rechazada">Rechazada</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Comentarios (opcional)
        </label>
        <textarea
          {...register('comentarios')}
          rows={2}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={createGuardia.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {createGuardia.isPending ? 'Guardando...' : 'Registrar guardia'}
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
