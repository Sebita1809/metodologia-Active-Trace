/**
 * components/umbral/UmbralView.tsx — Umbral configuration sub-view.
 *
 * - GET /api/calificaciones/umbral → show current threshold
 * - PUT /api/calificaciones/umbral → update threshold (RHF + Zod validation)
 * - Default 60 % when not configured (per backend RN-01/RN-02)
 *
 * < 200 LOC, no `any`, no class components.
 */

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useUmbral, useUpsertUmbral } from '../../hooks/useCalificaciones'
import { umbralFormSchema, type UmbralForm } from '../../types/schemas'

interface UmbralViewProps {
  asignacionId: string
}

export function UmbralView({ asignacionId }: UmbralViewProps) {
  const { data: umbral, isLoading } = useUmbral(asignacionId)

  const materiaId = umbral?.materia_id ?? ''
  const upsertMutation = useUpsertUmbral(asignacionId, materiaId)

  // Local state for the comma-separated string representation of valores_aprobatorios
  const [valoresText, setValoresText] = useState(
    'Satisfactorio, Supera lo esperado',
  )

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<UmbralForm>({
    resolver: zodResolver(umbralFormSchema),
    defaultValues: {
      umbral_pct: 60,
      valores_aprobatorios: ['Satisfactorio', 'Supera lo esperado'],
    },
  })

  useEffect(() => {
    if (umbral) {
      reset({
        umbral_pct: umbral.umbral_pct,
        valores_aprobatorios: umbral.valores_aprobatorios,
      })
      setValoresText(umbral.valores_aprobatorios.join(', '))
    }
  }, [umbral, reset])

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando umbral...</p>
  }

  function handleValoresBlur(e: React.FocusEvent<HTMLInputElement>) {
    const parsed = e.target.value
      .split(',')
      .map((v) => v.trim())
      .filter(Boolean)
    setValue('valores_aprobatorios', parsed, { shouldValidate: true })
  }

  async function onSubmit(data: UmbralForm) {
    await upsertMutation.mutateAsync({
      umbral_pct: data.umbral_pct,
      valores_aprobatorios: data.valores_aprobatorios,
    })
  }

  return (
    <div className="space-y-6 max-w-md">
      <h2 className="text-base font-semibold text-gray-900">
        Umbral de aprobación
      </h2>

      {umbral && (
        <div className="rounded-md bg-blue-50 p-3 text-sm text-blue-800">
          Umbral actual:{' '}
          <strong>{umbral.umbral_pct} %</strong> — Valores aprobatorios:{' '}
          {umbral.valores_aprobatorios.join(', ')}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label
            htmlFor="umbral-pct"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Umbral (%)
          </label>
          <input
            id="umbral-pct"
            type="number"
            min={0}
            max={100}
            {...register('umbral_pct', { valueAsNumber: true })}
            className="w-24 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.umbral_pct && (
            <p className="mt-1 text-xs text-red-600">
              {errors.umbral_pct.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="valores-aprobatorios"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Valores aprobatorios (separados por coma)
          </label>
          <input
            id="valores-aprobatorios"
            type="text"
            value={valoresText}
            onChange={(e) => setValoresText(e.target.value)}
            onBlur={handleValoresBlur}
            placeholder="Satisfactorio, Supera lo esperado"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Ingresá cada valor aprobatorio separado por coma.
          </p>
          {errors.valores_aprobatorios && (
            <p className="mt-1 text-xs text-red-600">
              {String(errors.valores_aprobatorios.message)}
            </p>
          )}
        </div>

        {upsertMutation.isError && (
          <div className="rounded-md bg-red-50 p-3">
            <p className="text-sm text-red-700">
              Error al guardar el umbral. Intentá de nuevo.
            </p>
          </div>
        )}

        {upsertMutation.isSuccess && (
          <div className="rounded-md bg-green-50 p-3">
            <p className="text-sm text-green-700">Umbral actualizado.</p>
          </div>
        )}

        <button
          type="submit"
          disabled={upsertMutation.isPending || !materiaId}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {upsertMutation.isPending ? 'Guardando...' : 'Guardar umbral'}
        </button>
      </form>
    </div>
  )
}
