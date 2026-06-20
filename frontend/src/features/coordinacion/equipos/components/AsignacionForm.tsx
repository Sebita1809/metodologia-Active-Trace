/**
 * AsignacionForm.tsx — Form to create a single asignacion (RHF + Zod).
 *
 * Fields: materia, carrera, cohorte, rol, docente, vigencia_desde, vigencia_hasta.
 * Validates fecha_hasta > fecha_desde.
 * < 200 LOC, no `any`, no class components.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { asignacionFormSchema, type AsignacionFormValues } from '../../schemas'
import { useCreateAsignacion } from '../hooks/useEquipos'

const ROLES = ['TUTOR', 'PROFESOR', 'COORDINADOR']

interface AsignacionFormProps {
  onSuccess?: () => void
}

export function AsignacionForm({ onSuccess }: AsignacionFormProps) {
  const createMutation = useCreateAsignacion()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AsignacionFormValues>({
    resolver: zodResolver(asignacionFormSchema),
    defaultValues: { rol: 'TUTOR' },
  })

  function onSubmit(values: AsignacionFormValues) {
    createMutation.mutate(
      {
        usuario_id: values.usuario_id,
        rol: values.rol,
        desde: values.desde,
        hasta: values.hasta ?? null,
        materia_id: values.materia_id ?? null,
        carrera_id: values.carrera_id ?? null,
        cohorte_id: values.cohorte_id ?? null,
        responsable_id: values.responsable_id ?? null,
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
          ID Docente
        </label>
        <input
          {...register('usuario_id')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="UUID del docente"
        />
        {errors.usuario_id && (
          <p className="text-red-600 text-xs mt-1">{errors.usuario_id.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Rol
        </label>
        <select
          {...register('rol')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        {errors.rol && (
          <p className="text-red-600 text-xs mt-1">{errors.rol.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Vigencia desde
        </label>
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
          Vigencia hasta (opcional)
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

      {createMutation.isError && (
        <p className="text-red-600 text-sm">
          Error al crear la asignación. Intentá nuevamente.
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting || createMutation.isPending}
        className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
      >
        {createMutation.isPending ? 'Guardando...' : 'Crear asignación'}
      </button>
    </form>
  )
}
