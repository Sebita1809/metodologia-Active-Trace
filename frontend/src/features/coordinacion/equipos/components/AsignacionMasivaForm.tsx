/**
 * AsignacionMasivaForm.tsx — Bulk assignment form (RHF + Zod).
 *
 * Multi-select docentes + materia × carrera × cohorte × rol + vigencia.
 * Shows partial result (éxitos/errores) after submission.
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { asignacionMasivaFormSchema, type AsignacionMasivaFormValues } from '../../schemas'
import { useCreateMasiva } from '../hooks/useEquipos'
import type { AsignacionMasivaResult } from '../types'

const ROLES = ['TUTOR', 'PROFESOR', 'COORDINADOR']

interface AsignacionMasivaFormProps {
  onSuccess?: () => void
}

export function AsignacionMasivaForm({ onSuccess }: AsignacionMasivaFormProps) {
  const createMasiva = useCreateMasiva()
  const [result, setResult] = useState<AsignacionMasivaResult | null>(null)
  const [docenteInput, setDocenteInput] = useState('')
  const [docenteIds, setDocenteIds] = useState<string[]>([])

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors },
  } = useForm<AsignacionMasivaFormValues>({
    resolver: zodResolver(asignacionMasivaFormSchema),
    defaultValues: { usuario_ids: [], rol: 'TUTOR' },
  })

  function addDocente() {
    if (!docenteInput.trim()) return
    const newIds = [...docenteIds, docenteInput.trim()]
    setDocenteIds(newIds)
    setValue('usuario_ids', newIds)
    setDocenteInput('')
  }

  function removeDocente(id: string) {
    const newIds = docenteIds.filter((d) => d !== id)
    setDocenteIds(newIds)
    setValue('usuario_ids', newIds)
  }

  function onSubmit(values: AsignacionMasivaFormValues) {
    createMasiva.mutate(
      {
        usuario_ids: values.usuario_ids,
        rol: values.rol,
        desde: values.desde,
        hasta: values.hasta ?? null,
        materia_id: values.materia_id ?? null,
        carrera_id: values.carrera_id ?? null,
        cohorte_id: values.cohorte_id ?? null,
      },
      {
        onSuccess: (data) => {
          setResult(data)
          reset()
          setDocenteIds([])
          onSuccess?.()
        },
      },
    )
  }

  return (
    <div className="space-y-4 max-w-lg">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Docentes (agregar por UUID)
          </label>
          <div className="flex gap-2">
            <input
              value={docenteInput}
              onChange={(e) => setDocenteInput(e.target.value)}
              className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm"
              placeholder="UUID del docente"
            />
            <button
              type="button"
              onClick={addDocente}
              className="bg-gray-100 text-gray-700 px-3 py-2 rounded text-sm hover:bg-gray-200"
            >
              Agregar
            </button>
          </div>
          {docenteIds.length > 0 && (
            <ul className="mt-2 space-y-1">
              {docenteIds.map((id) => (
                <li key={id} className="flex items-center gap-2 text-sm text-gray-700">
                  <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">
                    {id}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeDocente(id)}
                    className="text-red-500 hover:text-red-700 text-xs"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
          {errors.usuario_ids && (
            <p className="text-red-600 text-xs mt-1">{errors.usuario_ids.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Rol</label>
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

        <button
          type="submit"
          disabled={createMasiva.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {createMasiva.isPending ? 'Procesando...' : 'Asignar masivamente'}
        </button>
      </form>

      {result && (
        <div className="mt-4 p-4 bg-gray-50 rounded border border-gray-200 text-sm">
          <p className="font-medium text-gray-800 mb-2">
            Resultado: {result.exitosos} exitosos / {result.fallidos} fallidos
          </p>
          {result.resultados.filter((r) => !r.success).map((r) => (
            <p key={r.usuario_id} className="text-red-600 text-xs">
              {r.usuario_id}: {r.error}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
