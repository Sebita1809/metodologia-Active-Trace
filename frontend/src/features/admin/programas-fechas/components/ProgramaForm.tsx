/**
 * ProgramaForm.tsx — RHF+Zod form for uploading a programa de materia.
 *
 * Fields: carrera (select), cohorte (select), materia (select), titulo, referencia_archivo.
 * Note: Backend uses JSON body (NOT multipart). referencia_archivo is a string reference.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ProgramaSchema, type ProgramaData } from '../types/schemas'
import { useCarreras, useCohortes, useMaterias } from '@/features/admin/estructura/hooks/useEstructura'

interface ProgramaFormProps {
  onSubmit: (data: ProgramaData) => void
  onCancel: () => void
  isPending: boolean
}

export function ProgramaForm({ onSubmit, onCancel, isPending }: ProgramaFormProps) {
  const { data: carreras, isLoading: loadingCarreras } = useCarreras()
  const { data: cohortes, isLoading: loadingCohortes } = useCohortes()
  const { data: materias, isLoading: loadingMaterias } = useMaterias()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProgramaData>({
    resolver: zodResolver(ProgramaSchema),
    defaultValues: {
      materia_id: '',
      carrera_id: '',
      cohorte_id: '',
      titulo: '',
      referencia_archivo: '',
    },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Carrera <span className="text-red-500">*</span>
        </label>
        <select
          {...register('carrera_id')}
          disabled={loadingCarreras}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Seleccionar carrera...</option>
          {carreras?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.codigo} — {c.nombre}
            </option>
          ))}
        </select>
        {errors.carrera_id && (
          <p className="text-xs text-red-600">{errors.carrera_id.message}</p>
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
              {c.nombre} ({c.anio})
            </option>
          ))}
        </select>
        {errors.cohorte_id && (
          <p className="text-xs text-red-600">{errors.cohorte_id.message}</p>
        )}
      </div>

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
          Título <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          {...register('titulo')}
          placeholder="Título del programa..."
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.titulo && (
          <p className="text-xs text-red-600">{errors.titulo.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Referencia de archivo <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          {...register('referencia_archivo')}
          placeholder="URL o ruta del programa (PDF/DOCX)..."
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.referencia_archivo && (
          <p className="text-xs text-red-600">{errors.referencia_archivo.message}</p>
        )}
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
          {isPending ? 'Guardando...' : 'Subir programa'}
        </button>
      </div>
    </form>
  )
}
