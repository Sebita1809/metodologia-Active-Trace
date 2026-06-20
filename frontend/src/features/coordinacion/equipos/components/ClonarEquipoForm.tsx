/**
 * ClonarEquipoForm.tsx — Clone team form (RHF + Zod).
 *
 * Selector de origen (materia × carrera × cohorte) + selector de destino.
 * Warns if destino already has asignaciones.
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { clonarEquipoFormSchema, type ClonarEquipoFormValues } from '../../schemas'
import { useClonarEquipo, useAsignaciones } from '../hooks/useEquipos'

interface ClonarEquipoFormProps {
  onSuccess?: () => void
}

export function ClonarEquipoForm({ onSuccess }: ClonarEquipoFormProps) {
  const clonar = useClonarEquipo()
  const [showWarning, setShowWarning] = useState(false)
  const [pendingValues, setPendingValues] = useState<ClonarEquipoFormValues | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ClonarEquipoFormValues>({
    resolver: zodResolver(clonarEquipoFormSchema),
  })

  const destinoMateriaId = watch('destino_materia_id')
  const destinoCarreraId = watch('destino_carrera_id')
  const destinoCohorteId = watch('destino_cohorte_id')

  const { data: destinoAsignaciones } = useAsignaciones(
    destinoMateriaId && destinoCarreraId && destinoCohorteId
      ? {
          materia_id: destinoMateriaId,
          carrera_id: destinoCarreraId,
          cohorte_id: destinoCohorteId,
        }
      : undefined,
  )

  const destinoTieneAsignaciones =
    destinoAsignaciones !== undefined && destinoAsignaciones.length > 0

  function onSubmit(values: ClonarEquipoFormValues) {
    if (destinoTieneAsignaciones && !showWarning) {
      setPendingValues(values)
      setShowWarning(true)
      return
    }
    ejecutarClonado(values)
  }

  function ejecutarClonado(values: ClonarEquipoFormValues) {
    clonar.mutate(
      {
        origen_materia_id: values.origen_materia_id,
        origen_carrera_id: values.origen_carrera_id,
        origen_cohorte_id: values.origen_cohorte_id,
        destino_materia_id: values.destino_materia_id,
        destino_carrera_id: values.destino_carrera_id,
        destino_cohorte_id: values.destino_cohorte_id,
        desde: values.desde ?? null,
        hasta: values.hasta ?? null,
      },
      {
        onSuccess: () => {
          setShowWarning(false)
          setPendingValues(null)
          onSuccess?.()
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 max-w-lg">
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-gray-800">Equipo origen</h3>
        {['origen_materia_id', 'origen_carrera_id', 'origen_cohorte_id'].map((field) => (
          <div key={field}>
            <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">
              {field.replace('origen_', '').replace('_id', '')}
            </label>
            <input
              {...register(field as keyof ClonarEquipoFormValues)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              placeholder="UUID"
            />
            {errors[field as keyof ClonarEquipoFormValues] && (
              <p className="text-red-600 text-xs mt-1">
                {errors[field as keyof ClonarEquipoFormValues]?.message}
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-gray-800">Equipo destino</h3>
        {['destino_materia_id', 'destino_carrera_id', 'destino_cohorte_id'].map((field) => (
          <div key={field}>
            <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">
              {field.replace('destino_', '').replace('_id', '')}
            </label>
            <input
              {...register(field as keyof ClonarEquipoFormValues)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              placeholder="UUID"
            />
            {errors[field as keyof ClonarEquipoFormValues] && (
              <p className="text-red-600 text-xs mt-1">
                {errors[field as keyof ClonarEquipoFormValues]?.message}
              </p>
            )}
          </div>
        ))}
      </div>

      {destinoTieneAsignaciones && (
        <div className="bg-yellow-50 border border-yellow-300 rounded p-3 text-sm text-yellow-800">
          El destino ya tiene {destinoAsignaciones.length} asignación(es). Al clonar se agregarán nuevas asignaciones.
        </div>
      )}

      {showWarning && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => pendingValues && ejecutarClonado(pendingValues)}
            disabled={clonar.isPending}
            className="bg-yellow-600 text-white px-4 py-2 rounded text-sm hover:bg-yellow-700 disabled:opacity-50"
          >
            Confirmar clonado igualmente
          </button>
          <button
            type="button"
            onClick={() => setShowWarning(false)}
            className="bg-gray-200 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300"
          >
            Cancelar
          </button>
        </div>
      )}

      {!showWarning && (
        <button
          type="submit"
          disabled={clonar.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {clonar.isPending ? 'Clonando...' : 'Clonar equipo'}
        </button>
      )}
    </form>
  )
}
